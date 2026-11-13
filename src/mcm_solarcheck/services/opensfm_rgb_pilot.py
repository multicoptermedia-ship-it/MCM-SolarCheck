"""Local job adapter for the qualified OpenSfM engine; no photogrammetry here.

The shared API accepts explicitly selected RGB or Thermal records. SQLite selection and desktop UI
stay in the launcher; a later server worker can use the same job API.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import file_digest
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import time
import unicodedata

from mcm_solarcheck.services.colmap_openmvs_pilot import (
    PilotCancelled, PilotError, PilotProcessExit, PilotTimeout,
    _execute, _regular, input_signature, ThermalPilotFrame,
)
from mcm_solarcheck.services.micmac_orthophotos import MicMacCancelled, MicMacError, _copy_source
from mcm_solarcheck.services.orthomosaic_geotiff_contract import inspect_existing_geotiff


ENGINE_SOURCE = '8b6b77efddebf4429044d3206c7dc21c4e767e08'
STAGES = ('extract_metadata', 'detect_features', 'match_features', 'create_tracks',
          'reconstruct', 'undistort', 'dense_clustering', 'compute_depthmaps',
          'fuse_depthmaps', 'dense_merging')
# Existing upstream settings only. This is a bounded 2-GiB pilot profile,
# not a demonstrated memory guarantee or a final PV-resolution preset.
PROFILE = {
    'processes': 4, 'io_processes': 2, 'proj_cdn_enabled': False,
    'feature_type': 'HAHOG', 'feature_process_size': 2048,
    'matcher_type': 'OPENCL_BF', 'matching_gps_neighbors': 12,
    'matching_gps_distance': 0, 'matching_time_neighbors': 6,
    'matching_order_neighbors': 6, 'matching_vlad_neighbors': 0,
    'matching_bow_neighbors': 0, 'use_altitude_tag': True,
    'undistorted_image_max_size': 4000, 'depthmap_max_image_size': 1600,
    'depthmap_num_neighbors': 6, 'depthmap_num_matching_views': 4,
    'depthmap_cluster_max_size': 8, 'depthmap_max_cluster_views': 16,
    'dsm_enabled': True,
}
LABELS = ('Metadaten', 'RGB-Merkmale', 'Bildabgleich', 'Bildspuren', 'Kameraverbund',
          'Entzerrung', 'Dense-Cluster', 'Tiefenkarten', 'Fusion', 'RGB-GeoTIFF')


@dataclass(frozen=True)
class OpenSfMPilotConfig:
    # E.g. (python,) or (conda, run, --prefix, prefix, python). No shell.
    engine_command: tuple[str, ...]
    runner: Path
    output_parent: Path
    stage_timeout_seconds: float = 3600
    total_timeout_seconds: float = 10800
    project_label: str = 'Projekt'
    modality: str = 'rgb'


@dataclass(frozen=True)
class OpenSfMPilotResult:
    workspace: Path
    rgb_geotiff: Path
    rgb_images: int
    registered_images: int


@dataclass(frozen=True)
class OpenSfMThermalPilotResult:
    workspace: Path
    thermal_geotiff: Path
    thermal_images: int
    registered_images: int


def report_modality(report):
    return 'thermal' if report.get('pipeline') == 'opensfm_thermal' else 'rgb'


def image_count(report):
    return report.get(report_modality(report) + '_images')


def pilot_result(workspace, ortho, count, registered, modality):
    result_type = OpenSfMThermalPilotResult if modality == 'thermal' else OpenSfMPilotResult
    return result_type(workspace, ortho, count, registered)


THERMAL_INPUT_FAILURES = ('raw_raster', 'preview_unreadable', 'preview_format', 'preview_dimensions')


class ThermalInputError(PilotError):
    """A fixed, shareable reason; never paths, image names or raw measurements."""
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


def _require_thermal_copy(path):
    # Both JPEG and MPO are supported by the existing M3T importer. Inspect only
    # the primary rendered component used by OpenSfM/OpenCV; never silently select
    # a different component, resize it or strip the radiometric APP3/4/5 payload.
    from PIL import Image
    from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser, M3TFormatError
    try:
        raw = M3TRadiometricParser().parse_file(path)
    except (OSError, M3TFormatError):
        raise ThermalInputError('raw_raster',
            'Thermaldateien gefunden; das eingebettete M3T-16-Bit-Raster einer Arbeitskopie '
            'ist nicht mit dem vorhandenen Parser lesbar. Kennzahlen kopieren; kein Neuimport.') from None
    try:
        with Image.open(path) as picture:
            if picture.format not in ('JPEG', 'MPO'):
                raise ThermalInputError('preview_format',
                    'Thermal-Rohdaten lesbar; die Darstellung ist kein JPEG/MPO. Kennzahlen kopieren.')
            if picture.size != (raw.width, raw.height):
                raise ThermalInputError('preview_dimensions',
                    'Thermal-Rohdaten lesbar; das erste JPEG/MPO-Bild passt nicht zum 640x512-Raster. '
                    'Keine automatische Bildteilwahl oder Skalierung. Kennzahlen kopieren.')
            picture.verify()
    except (OSError, ValueError, SyntaxError):
        raise ThermalInputError('preview_unreadable',
            'Thermal-Rohdaten lesbar; die JPEG/MPO-Darstellung ist nicht lesbar. Kennzahlen kopieren.') from None


def require_thermal_metadata(workspace, expected):
    for name in expected:
        meta = _json(workspace / 'exif' / (name + '.exif'))
        focal = meta.get('focal_ratio')
        if (meta.get('width') != 640 or meta.get('height') != 512
                or type(focal) not in (int, float) or not math.isfinite(focal) or focal <= 0
                or not isinstance(meta.get('camera'), str) or not meta['camera']):
            raise PilotError('Thermal-Sensorgeometrie in OpenSfM-Metadaten fehlt; '
                             'keine RGB-Kalibrierung oder geratene Brennweite einsetzen.')


def require_thermal_geometry(workspace, expected):
    models = _json(workspace / 'reconstruction.json')
    if not reconstruction_summary(workspace / 'reconstruction.json', expected)['registration_complete']:
        raise PilotError('Kein vollstaendiger Thermal-Kameraverbund.')
    for name, shot in models[0]['shots'].items():
        meta = _json(workspace / 'exif' / (name + '.exif'))
        cam = models[0]['cameras'][shot['camera']]
        focal = cam.get('focal') if isinstance(cam, dict) else None
        if (shot['camera'] != meta['camera'] or cam.get('width') != 640 or cam.get('height') != 512
                or cam.get('projection_type') != 'perspective'
                or type(focal) not in (int, float) or not math.isfinite(focal) or focal <= 0):
            raise PilotError('Thermal-Kameramodell passt nicht zu den eigenen Sensordaten; '
                             'keine RGB-Kalibrierung uebernehmen.')


def _json(path):
    source = _regular(path)
    if source.stat().st_size > 256 * 1024 * 1024:
        raise PilotError('OpenSfM-Ergebnisdatei fuer diesen Pilot unerwartet gross.')
    try:
        return json.loads(source.read_text(encoding='utf-8'))
    except (UnicodeError, ValueError):
        raise PilotError('OpenSfM-Ergebnisdatei ungueltig; lokale Protokolle pruefen.') from None


METRIC_KEYS = ('pipeline', 'run_id', 'started_at', 'status', 'rgb_images', 'registered_images',
               'registration_complete', 'models', 'missing_images', 'foreign_images', 'points',
               'orthophoto_created', 'georeferencing_verified', 'temperature_verified',
               'thermal_created', 'elapsed_seconds', 'steps', 'stored_depthmaps',
               'thermal_images', 'thermal_value_kind', 'radiometric_sources_preserved',
               'temperature_matrix_created', 'thermal_input_failure', 'points_scope', 'matching_supplement')


def _stored_depthmaps(workspace):
    directory = Path(workspace) / 'undistorted' / 'depthmaps'
    # Presence counts only, not validation of LZ4-wrapped engine caches.
    return {name: sum(path.is_file() and not path.is_symlink() for path in directory.glob('*.' + name + '.npz'))
            for name in ('raw', 'clean')}


def read_opensfm_metrics(workspace):
    """Return only shareable fields; refuse COLMAP/other-engine reports."""
    workspace = Path(workspace)
    manifest = _json(workspace / 'job.json')
    if (not isinstance(manifest, dict) or manifest.get('expected_engine_source') != ENGINE_SOURCE):
        raise PilotError('Kein OpenSfM-Laufordner. Bitte den Ordner des OpenSfM-Piloten waehlen.')
    if manifest.get('pipeline', 'opensfm_rgb') not in ('opensfm_rgb', 'opensfm_thermal'):
        raise PilotError('Unbekannte OpenSfM-Bildart.')
    modality = report_modality(manifest)
    kind = 'THERMAL' if modality == 'thermal' else 'RGB'
    pipeline = 'opensfm_' + modality
    filename = manifest.get('metrics_filename', 'laufzeiten.json')
    if (not isinstance(filename, str) or (filename != 'laufzeiten.json' and not re.fullmatch(
            rf'OpenSfM_{kind}_[0-9]{{8}}_[0-9]{{6}}_[a-z0-9_]{{8}}_Kennzahlen[.]json', filename))):
        raise PilotError('OpenSfM-Kennzahlendatei hat einen ungueltigen Namen.')
    report = _json(workspace / filename)
    if (not isinstance(report, dict) or report.get('pipeline', 'opensfm_rgb') != pipeline
            or report.get('status') not in ('running', 'finished', 'failed', 'cancelled')):
        raise PilotError('Kein gueltiger OpenSfM-Kennzahlenbericht.')
    steps = report.get('steps')
    if not isinstance(steps, list) or len(steps) > len(STAGES):
        raise PilotError('Kein gueltiger OpenSfM-Stufenbericht.')
    safe_steps = []
    for index, item in enumerate(steps):
        if (not isinstance(item, dict) or item.get('stage') != STAGES[index]
                or item.get('status') not in ('running', 'finished', 'failed', 'cancelled')):
            raise PilotError('Dieser Bericht gehoert nicht zum OpenSfM-Piloten.')
        if 'reused' in item and type(item['reused']) is not bool:
            raise PilotError('Ungueltige Wiederverwendungskennzahl.')
        for key in ('seconds', 'timeout_seconds', 'exit_code'):
            value = item.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise PilotError('OpenSfM-Kennzahlen enthalten ungueltige Zahlen.')
        if item.get('failure_kind') not in (None, 'timeout', 'process_exit'):
            raise PilotError('OpenSfM-Kennzahlen enthalten einen unbekannten Fehlerstatus.')
        safe_steps.append({k: item[k] for k in ('stage', 'status', 'seconds', 'timeout_seconds',
                                               'failure_kind', 'exit_code', 'reused') if k in item})
    safe = {key: report[key] for key in METRIC_KEYS if key in report and key != 'steps'}
    for key in ('thermal_images', 'radiometric_sources_preserved', 'rgb_images', 'registered_images', 'models', 'missing_images', 'foreign_images', 'points', 'elapsed_seconds'):
        if key in safe and (type(safe[key]) not in (int, float) or not math.isfinite(safe[key]) or safe[key] < 0):
            raise PilotError('OpenSfM-Kennzahlen enthalten ungueltige Zahlen.')
    for key in ('registration_complete', 'orthophoto_created', 'georeferencing_verified', 'temperature_verified', 'thermal_created', 'temperature_matrix_created'):
        if key in safe and type(safe[key]) is not bool:
            raise PilotError('OpenSfM-Kennzahlen enthalten einen ungueltigen Status.')
    if 'run_id' in safe and not re.fullmatch(rf'opensfm-{modality}-[0-9]{{8}}-[0-9]{{6}}-[a-z0-9_]{{8}}', str(safe['run_id'])):
        raise PilotError('OpenSfM-Laufkennung ungueltig.')
    if 'started_at' in safe:
        try:
            datetime.fromisoformat(safe['started_at'])
        except (TypeError, ValueError):
            raise PilotError('OpenSfM-Laufdatum ungueltig.') from None
    if safe.get('matching_supplement') is not None:
        from .opensfm_sparse_bridge import supplement_metrics
        safe['matching_supplement'] = supplement_metrics(safe['matching_supplement'])
    if safe.get('points_scope') not in (None, 'sum_per_model'):
        raise PilotError('Ungueltige Punktzaehlweise.')
    if safe.get('thermal_input_failure') not in (None, *THERMAL_INPUT_FAILURES):
        raise PilotError('Unbekannter Thermal-Eingabepruefstatus.')
    if modality == 'thermal':
        if (report.get('thermal_value_kind') != 'visual' or report.get('temperature_matrix_created') is not False
                or report.get('temperature_verified') is not False or report.get('georeferencing_verified') is not False
                or report.get('rgb_images') != 0 or type(report.get('thermal_images')) is not int
                or not 3 <= report['thermal_images'] <= 300
                or type(report.get('radiometric_sources_preserved')) is not int
                or not 0 <= report['radiometric_sources_preserved'] <= report['thermal_images']):
            raise PilotError('Ungueltiger Thermal-Darstellungsbericht; keine Celsiusfreigabe.')
        safe['thermal_value_kind'] = 'visual'
    safe.update(pipeline=pipeline, steps=safe_steps, stored_depthmaps=_stored_depthmaps(workspace))
    if (report.get('registration_complete') is False and steps
            and steps[-1].get('stage') == 'reconstruct' and steps[-1].get('status') == 'finished'
            and report['status'] in ('failed', 'cancelled')):
        detail, total = saved_component_details(workspace, safe)
        safe['reconstruction_details'] = detail
        if total is not None:
            safe.update(points=total, points_scope='sum_per_model')
    return safe


def local_run_label(workspace):
    """Private desktop label, deliberately separate from shareable metrics."""
    workspace = Path(workspace)
    manifest = _json(workspace / 'job.json')
    project = str(manifest.get('project_label') or 'Projektname im aelteren Lauf nicht gespeichert')[:120]
    when = manifest.get('started_at')
    if when:
        try:
            stamp = 'Start ' + datetime.fromisoformat(when).strftime('%d.%m.%Y %H:%M:%S')
        except (ValueError, TypeError):
            raise PilotError('OpenSfM-Laufdatum ungueltig.') from None
    else:
        stamp = 'Berichtsstand ' + datetime.fromtimestamp((workspace / 'laufzeiten.json').stat().st_mtime).astimezone().strftime('%d.%m.%Y %H:%M:%S')
    kind = 'THERMAL' if report_modality(manifest) == 'thermal' else 'RGB'
    return f'OpenSfM {kind} · {project} · {stamp}\nOrdner: {workspace.name}'


CACHE_COUNTS = ('working_images', 'clusters', 'raw_readable', 'raw_unreadable',
                'clean_readable', 'clean_unreadable', 'foreign_cache_files',
                'clusters_fully_cached', 'clusters_partly_cached', 'clusters_without_cache',
                'clustered_images')


def _cache_result(report):
    if (not isinstance(report, dict) or report.get('check') != 'solarcheck-opensfm-cache-1'
            or report.get('status') not in ('completed', 'attention_required')
            or report.get('geometric_quality_verified') is not False
            or report.get('resume_implemented') is not False
            or type(report.get('changed_during_check')) is not bool
            or any(type(report.get(k)) is not int or not 0 <= report[k] <= 10000 for k in CACHE_COUNTS)):
        raise PilotError('Kein gueltiger OpenSfM-Cachepruefbericht.')
    safe = {k: report[k] for k in (*CACHE_COUNTS, 'check', 'status', 'changed_during_check',
                                  'geometric_quality_verified', 'resume_implemented')}
    if 'seconds' in report:
        value = report['seconds']
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise PilotError('Ungueltige Cachepruefdauer.')
        safe['seconds'] = value
    return safe


def read_opensfm_cache_metrics(workspace):
    """Reopen the newest saved inspection, never an unfinished worker result."""
    report = read_opensfm_metrics(workspace)
    candidates = []
    for directory in Path(workspace).glob('cache-check-*'):
        if not re.fullmatch(r'cache-check-[a-z0-9_]{8}', directory.name):
            continue
        path = directory / 'Kennzahlen.json'
        if path.is_file():
            candidates.append(_regular(path))
    if not candidates:
        return report
    saved = _json(max(candidates, key=lambda p: p.stat().st_mtime_ns))
    detail = saved.get('depthmap_cache_check', {}) if isinstance(saved, dict) else {}
    if not isinstance(detail, dict) or (isinstance(saved, dict) and saved.get('run_id') != report.get('run_id')):
        raise PilotError('Cachepruefbericht gehoert nicht zu diesem Lauf oder ist ungueltig.')
    if detail.get('status') in ('failed', 'timeout', 'cancelled'):
        report['depthmap_cache_check'] = {'check': 'solarcheck-opensfm-cache-1', 'status': detail['status'],
                                        'accepted_as_readable': False}
    else:
        report['depthmap_cache_check'] = _cache_result(detail)
    return report


def check_opensfm_depthmap_cache(workspace, config, *, should_cancel=None, executor=None):
    """Explicit bounded read of local engine outputs. No photo stages or repairs."""
    workspace = Path(workspace)
    report = read_opensfm_metrics(workspace)
    manifest = _json(workspace / 'job.json')
    if config.modality != report_modality(report):
        raise PilotError('RGB- und Thermal-Lauf getrennt waehlen.')
    if (report['status'] not in ('failed', 'cancelled') or not report.get('registration_complete')
            or len(report['steps']) < 8
            or any(s['status'] != 'finished' for s in report['steps'][:7])
            or manifest.get('profile') != PROFILE or _json(workspace / 'config.yaml') != PROFILE):
        raise PilotError('Cachepruefung benoetigt einen gestoppten OpenSfM-Dense-Lauf mit unveraendertem Profil.')
    if (not workspace.is_absolute() or any(p.is_symlink() for p in (workspace, *workspace.parents))
            or any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file()
                   for p in (workspace, *workspace.parents))):
        raise PilotError('Privaten lokalen OpenSfM-Laufordner ausserhalb Git auswaehlen.')
    if not config.engine_command or any(not isinstance(p, str) or not p or '\0' in p for p in config.engine_command):
        raise PilotError('Vorhandener OpenSfM-Aufruf fehlt.')
    executable = Path(config.engine_command[0])
    _regular(executable.resolve(strict=True))
    worker = _regular(Path(config.runner).with_name('MCM_SolarCheck_OPENSFM_CACHE_WORKER.py'))
    cancel = should_cancel or (lambda: False)
    if cancel():
        raise PilotCancelled('Cachepruefung abgebrochen.')
    inspection = Path(tempfile.mkdtemp(prefix='cache-check-', dir=workspace))
    runtime_env = {'TEMP': str(inspection), 'TMP': str(inspection),
                   'MPLCONFIGDIR': str(inspection), 'VSCMD_SKIP_SENDTELEMETRY': '1'}
    detail = {'check': 'solarcheck-opensfm-cache-1', 'status': 'failed', 'accepted_as_readable': False}
    tick = time.monotonic()
    try:
        (executor or _execute)(executable,
            (*config.engine_command[1:], '-I', str(worker), str(workspace), str(inspection)),
            workspace, inspection / 'worker.log', cancel, timeout=600, env_overrides=runtime_env)
        detail = _cache_result(_json(inspection / 'worker-result.json'))
    except PilotTimeout:
        detail['status'] = 'timeout'
        raise PilotTimeout('Cachepruefung nach zehn Minuten beendet; vorhandene Dateien bleiben erhalten.') from None
    except PilotCancelled:
        detail['status'] = 'cancelled'
        raise
    except (OSError, PilotError):
        raise PilotError('Cachepruefung fehlgeschlagen; worker.log im neuen cache-check-Unterordner bleibt lokal.') from None
    finally:
        detail['seconds'] = round(time.monotonic() - tick, 3)
        report['depthmap_cache_check'] = detail
        with (inspection / 'Kennzahlen.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
    return report


def reconstruction_summary(path, expected):
    """Read an existing engine result, never compute/merge camera poses."""
    models = _json(path)
    if not isinstance(models, list):
        raise PilotError('OpenSfM-Kameraverbund hat ein ungueltiges Format.')
    names = set()
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get('shots'), dict):
            raise PilotError('OpenSfM-Kameraverbund hat ein ungueltiges Format.')
        names.update(model['shots'])
    result = {'points': sum(len(m.get('points', {})) if isinstance(m.get('points'), dict) else 0 for m in models),
              'points_scope': 'sum_per_model', 'models': len(models), 'registered_images': len(names),
              'missing_images': len(expected - names), 'foreign_images': len(names - expected)}
    complete = len(models) == 1 and names == expected
    if complete:
        model = models[0]
        cameras = model.get('cameras')
        points = model.get('points')
        complete = isinstance(cameras, dict) and isinstance(points, dict) and bool(points)
        if complete:
            for shot in model['shots'].values():
                if (not isinstance(shot, dict) or not isinstance(shot.get('camera'), str)
                        or shot['camera'] not in cameras):
                    complete = False
                    break
                for key in ('rotation', 'translation'):
                    values = shot.get(key)
                    if (not isinstance(values, list) or len(values) != 3
                            or any(type(v) not in (float, int) or not math.isfinite(v) for v in values)):
                        complete = False
        result['points'] = len(points) if isinstance(points, dict) else 0
        if complete:
            for point in points.values():
                values = point.get('coordinates') if isinstance(point, dict) else None
                if (not isinstance(values, list) or len(values) != 3
                        or any(type(v) not in (float, int) or not math.isfinite(v) for v in values)):
                    complete = False
                    break
    result['registration_complete'] = bool(complete)
    return result


def saved_component_details(workspace, report):
    """Count stored model records/ID overlaps; no images, EXIF, engine or writes.

    Shared track IDs are merely candidates for an upstream geometric check.
    They do not establish transform, inliers, complete registration or quality.
    """
    paths = [Path(workspace) / name for name in ('reconstruction.json', 'input-map.json')]
    fallback = {'status': 'unreadable', 'geometric_quality_verified': False}
    try:
        before = [(p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ino) for p in paths]
        models, mapping = (_json(p) for p in paths)
        if (not isinstance(models, list) or not 1 <= len(models) <= 300
                or not isinstance(mapping, list) or len(mapping) != image_count(report)):
            raise PilotError('invalid_saved_components')
        expected = []
        for item in mapping:
            name = item.get('working_name') if isinstance(item, dict) else None
            if not isinstance(name, str) or not re.fullmatch(r'[0-9]{6}[.]JPG', name):
                raise PilotError('invalid_saved_components')
            expected.append(name)
        if len(set(expected)) != len(expected):
            raise PilotError('invalid_saved_components')
        shot_sets, point_sets, components = [], [], []
        for index, model in enumerate(models):
            if (not isinstance(model, dict) or any(not isinstance(model.get(k), dict)
                    for k in ('shots', 'points', 'cameras'))):
                raise PilotError('invalid_saved_components')
            shot_sets.append(set(model['shots']))
            point_sets.append(set(model['points']))
            components.append(dict(model_index=index, images=len(shot_sets[-1]),
                point_records=len(point_sets[-1]), cameras=len(model['cameras'])))
        names = set().union(*shot_sets)
        if (len(models) != report.get('models') or len(names) != report.get('registered_images')
                or len(set(expected) - names) != report.get('missing_images')
                or len(names - set(expected)) != report.get('foreign_images')):
            return {'status': 'counts_mismatch', 'geometric_quality_verified': False}, None
        pairs = [dict(model_a=i, model_b=j, shared_images=len(shot_sets[i] & shot_sets[j]),
                      shared_point_ids=len(point_sets[i] & point_sets[j]))
                 for i in range(len(models)) for j in range(i + 1, len(models))]
        after = [(p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ino) for p in paths]
        if before != after:
            return {'status': 'changed_during_read', 'geometric_quality_verified': False}, None
        total = sum(item['point_records'] for item in components)
        return dict(status='completed', components=components, pairs=pairs,
            unique_registered_images=len(names), point_records=total,
            point_count_scope='sum_per_model', geometric_quality_verified=False), total
    except (OSError, PilotError, ValueError, TypeError):
        return fallback, None


def _require_engine_gps(workspace, expected):
    # Validate the engine's normal metadata output, without another EXIF reader
    # or an override that could discard DJI RTK/accuracy/camera information.
    for name in expected:
        metadata = _json(workspace / 'exif' / (name + '.exif'))
        try:
            gps = metadata['gps']
            coords = [float(gps[key]) for key in ('latitude', 'longitude', 'altitude')]
            valid = (all(math.isfinite(v) for v in coords)
                     and -90 <= coords[0] <= 90 and -180 <= coords[1] <= 180)
        except (ValueError, TypeError, KeyError):
            valid = False
        if not valid:
            raise PilotError('OpenSfM-Metadaten enthalten keine vollstaendigen Kamerapositionen; '
                             'keine geratenen GPS-/CRS-Werte einsetzen.')


def _inspect_visual_geotiff(workspace, stopped, *, modality='rgb'):
    """The same existing raster gate for an initial run and a continuation."""
    ortho = _regular(workspace / 'undistorted' / 'depthmaps' / 'ortho.tif')
    try:
        reference = inspect_existing_geotiff(ortho)
        import rasterio
        from rasterio.transform import Affine
        with rasterio.open(ortho) as raster:
            if (not raster.crs.is_projected or raster.count not in (3, 4)
                    or raster.transform == Affine.identity()):
                raise ValueError
            nonempty = False
            for _index, window in raster.block_windows(1):
                if stopped():
                    raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
                if raster.dataset_mask(window=window).any():
                    nonempty = True
                    break
            if not nonempty:
                raise ValueError
        return ortho, {'crs': reference.crs, 'width': reference.width, 'height': reference.height}
    except (PilotCancelled, PilotTimeout):
        raise
    except Exception:
        raise PilotError(f'OpenSfM-Ausgabe ohne verwendbares projiziertes {modality.upper()}-Darstellungs-GeoTIFF; keine CRS-Ergaenzung.') from None


def _validate_inputs(frames, config):
    if config.modality not in ('rgb', 'thermal'):
        raise PilotError('Unbekannte Bildart.')
    if any(isinstance(f, ThermalPilotFrame) != (config.modality == 'thermal') for f in frames):
        raise PilotError('RGB- und Thermal-Eingaben duerfen nicht gemischt werden.')
    if not 3 <= len(frames) <= 300 or len({f.frame_id for f in frames}) != len(frames):
        raise PilotError('Erster Pilot: vollstaendiges zusammengehoeriges Projekt mit 3 bis 300 JPGs der gewaehlten Bildart waehlen.')
    if (not math.isfinite(config.stage_timeout_seconds) or not 0 < config.stage_timeout_seconds <= 3600
            or not math.isfinite(config.total_timeout_seconds) or not 0 < config.total_timeout_seconds <= 10800):
        raise PilotError('Pilot ist auf maximal 60 Minuten je Stufe und drei Stunden insgesamt begrenzt.')
    if not config.engine_command or any(not isinstance(p, str) or not p or '\0' in p for p in config.engine_command):
        raise PilotError('OpenSfM-Prozessaufruf fehlt oder ist ungueltig.')
    # Software interpreter symlinks are normal in a Unix virtual environment;
    # keep the invocation path (and thus its prefix), validate its real target.
    _regular(Path(config.engine_command[0]).resolve(strict=True))
    _regular(config.runner)
    parent = Path(config.output_parent)
    if not parent.is_dir() or any(p.is_symlink() for p in (parent, *parent.parents)):
        raise PilotError('Vorhandenen privaten Ausgabeordner auswaehlen.')
    parent = parent.resolve(strict=True)
    if any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file() for p in (parent, *parent.parents)):
        raise PilotError('Pilot-Ausgabe muss ausserhalb eines Git-Checkouts liegen.')
    paths, total = set(), 0
    for frame in frames:
        source = Path(frame.source_file)
        if not source.is_absolute():
            raise PilotError('Importierte Bildquellen muessen absolute lokale Pfade haben.')
        source = _regular(source)
        if (source.suffix.lower() not in ('.jpg', '.jpeg') or source in paths
                or source.parent == parent or source.parent in parent.parents or parent in source.parents):
            raise PilotError('JPGs und davon getrennten Ausgabeordner waehlen; keine doppelten Quellen.')
        paths.add(source)
        try:
            coords = (float(frame.latitude), float(frame.longitude), float(frame.altitude_m))
        except (ValueError, TypeError):
            raise PilotError('Importierte Kamerapositionen fehlen; kein georeferenziertes Ergebnis behaupten.') from None
        if (not all(math.isfinite(v) for v in coords) or not -90 <= coords[0] <= 90
                or not -180 <= coords[1] <= 180):
            raise PilotError('Importierte Kamerapositionen sind ungueltig.')
        total += source.stat().st_size
    if shutil.disk_usage(parent).free < total * 4 + 512 * 1024 * 1024:
        raise PilotError('Privater Ausgabeordner hat zu wenig freien Platz fuer Arbeitskopien und Zwischenstaende.')
    return parent


def _run_opensfm_pilot(frames, config, *, should_cancel=None, on_progress=None,
                          inputs_unchanged=None, executor=None, on_workspace=None, _reuse=None):
    """Qualified standard stages -> checked existing GeoTIFF, no project writes."""
    frames = tuple(frames)
    cancel = should_cancel or (lambda: False)
    progress = on_progress or (lambda text: None)
    execute = executor or _execute
    if cancel():
        raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
    parent = _validate_inputs(frames, config)
    modality = config.modality
    kind = 'THERMAL' if modality == 'thermal' else 'RGB'
    began = datetime.now().astimezone()
    stamp = began.strftime('%Y%m%d_%H%M%S')
    label = unicodedata.normalize('NFKD', str(config.project_label)).encode('ascii', 'ignore').decode()
    slug = re.sub('[^A-Za-z0-9]+', '-', label).strip('-')[:32] or 'Projekt'
    workspace = Path(tempfile.mkdtemp(prefix=f'{stamp}_OpenSfM_{kind}_{slug}_', dir=parent))
    run_id = f'opensfm-{modality}-{stamp.replace("_", "-")}-{workspace.name[-8:]}'
    metrics_filename = f'OpenSfM_{kind}_{stamp}_{workspace.name[-8:]}_Kennzahlen.json'
    started = time.monotonic()
    deadline = started + config.total_timeout_seconds
    record = {'status': 'running', 'rgb_images': len(frames) if modality == 'rgb' else 0,
              'thermal_images': len(frames) if modality == 'thermal' else 0,
              'thermal_value_kind': 'visual' if modality == 'thermal' else None,
              'radiometric_sources_preserved': 0, 'temperature_matrix_created': False,
              'thermal_input_failure': None, 'registered_images': 0, 'matching_supplement': None,
              'pipeline': 'opensfm_' + modality, 'run_id': run_id, 'started_at': began.isoformat(timespec='seconds'),
              'project_label': str(config.project_label), 'metrics_filename': metrics_filename,
              'models': 0, 'missing_images': len(frames), 'foreign_images': 0, 'points': 0, 'points_scope': None,
              'registration_complete': False, 'orthophoto_created': False,
              'georeferencing_verified': False, 'temperature_verified': False,
              'thermal_created': False, 'steps': [], 'expected_engine_source': ENGINE_SOURCE,
              'input_signature': input_signature(frames), 'profile': PROFILE,
              'stage_timeout_seconds': config.stage_timeout_seconds,
              'total_timeout_seconds': config.total_timeout_seconds}

    if _reuse is not None:
        if modality != 'thermal':
            raise PilotError('Zusatzabgleich nur fuer Thermal.')
        record['bridge_plan'] = {'target_names': _reuse.targets, 'source_workspace': str(_reuse.source)}
        record['matching_supplement'] = dict(status='pending', target_images=len(_reuse.targets),
            candidate_pairs=0, previous_pairs_skipped=0, new_pairs=0, matched_pairs=0)

    def stopped():
        if time.monotonic() >= deadline:
            raise PilotTimeout('Gesamtzeitlimit des OpenSfM-Piloten erreicht; Arbeitsdateien bleiben erhalten.')
        return cancel()

    def save():
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        record['stored_depthmaps'] = _stored_depthmaps(workspace)
        temporary = workspace / 'job.next.json'
        temporary.write_text(json.dumps(record, indent=2), encoding='utf-8')
        temporary.replace(workspace / 'job.json')
        temporary = workspace / 'metrics.next.json'
        temporary.write_text(json.dumps({k: record[k] for k in METRIC_KEYS}, indent=2), encoding='utf-8')
        temporary.replace(workspace / metrics_filename)

    sources, mapping = [], []
    save()
    try:
        if on_workspace is not None:
            on_workspace(workspace)
        for name in ('tmp', 'matplotlib'):
            (workspace / name).mkdir()
        runtime_env = {'TEMP': str(workspace / 'tmp'), 'TMP': str(workspace / 'tmp'),
                       'MPLCONFIGDIR': str(workspace / 'matplotlib'),
                       'VSCMD_SKIP_SENDTELEMETRY': '1'}
        images = workspace / 'images'
        images.mkdir()
        for index, frame in enumerate(frames, 1):
            if stopped():
                raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
            progress(f'{kind}-Arbeitskopien {index}/{len(frames)}')
            name = f'{index:06d}.JPG'
            try:
                sources.append(_copy_source(asdict(frame), images / name, None, stopped))
            except MicMacCancelled:
                raise PilotCancelled('OpenSfM-Pilot abgebrochen.') from None
            except MicMacError:
                raise PilotError('RGB-Arbeitskopie fehlgeschlagen oder Quelle veraendert; Originale bleiben erhalten.') from None
            if modality == 'thermal' and _reuse is None:
                try:
                    _require_thermal_copy(images / name)
                except ThermalInputError as error:
                    record['thermal_input_failure'] = error.kind
                    raise
            if modality == 'thermal':
                record['radiometric_sources_preserved'] += 1
            digest = frame.content_sha256
            if not digest:
                with (images / name).open('rb') as stream:
                    digest = file_digest(stream, 'sha256').hexdigest()
            mapping.append({'working_name': name, 'frame_id': frame.frame_id,
                            'source_file': frame.source_file, 'content_sha256': digest})
        (workspace / 'input-map.json').write_text(json.dumps(mapping, indent=2), encoding='utf-8')
        # JSON is a YAML subset; no added app dependency or camera override.
        (workspace / 'config.yaml').write_text(json.dumps(PROFILE, indent=2), encoding='utf-8')
        expected = {item['working_name'] for item in mapping}
        if _reuse is not None:
            progress('Gespeicherte Thermal-Metadaten, Merkmale und Matches bytegleich uebernehmen.')
            _reuse.prepare(workspace, stopped)
        for index, (stage, label) in enumerate(zip(STAGES, (s.replace('RGB', kind) for s in LABELS)), 1):
            if _reuse is not None:
                _reuse.unchanged(force=True)
            if stopped():
                raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
            limit = min(config.stage_timeout_seconds, deadline - time.monotonic())
            progress(f'{index}/{len(STAGES)} OpenSfM: {label} (max. {limit / 60:.0f} min)')
            item = {'stage': stage, 'status': 'running', 'seconds': None,
                    'timeout_seconds': round(limit, 3)}
            record['steps'].append(item)
            save()
            tick = time.monotonic()
            log = workspace / f'step-{index:02d}.log'
            reused = _reuse is not None and index <= 2
            call_stage = 'match_missing' if _reuse is not None and stage == 'match_features' else stage
            arguments = (*config.engine_command[1:], '-I', str(config.runner), call_stage, str(workspace))
            if stage == 'dense_merging':
                arguments += ('--georeferenced',)
            try:
                if reused:
                    item['reused'] = True
                else:
                    execute(Path(config.engine_command[0]), arguments, workspace, log, stopped,
                            timeout=limit, env_overrides=runtime_env)
                if call_stage == 'match_missing':
                    from .opensfm_sparse_bridge import supplement_metrics
                    record['matching_supplement'] = supplement_metrics(_json(workspace / 'matching-supplement.json'))
                    if record['matching_supplement']['status'] != 'finished':
                        raise PilotError('Zusatzabgleich nicht vollstaendig beendet.')
                item['status'] = 'finished'
            except PilotProcessExit as error:
                item.update(status='failed', failure_kind='process_exit', exit_code=error.returncode)
                raise PilotError(f'OpenSfM {label}: Code {error.returncode}; {log.name} nur lokal pruefen.') from None
            except PilotCancelled:
                item['status'] = 'cancelled'
                raise
            except PilotTimeout:
                item.update(status='failed', failure_kind='timeout')
                raise PilotTimeout(f'OpenSfM {label}: Zeitlimit erreicht; {log.name} nur lokal pruefen.') from None
            except (OSError, PilotError):
                item['status'] = 'failed'
                raise PilotError(f'OpenSfM {label} fehlgeschlagen; {log.name} nur lokal pruefen.') from None
            finally:
                item['seconds'] = round(time.monotonic() - tick, 3)
                save()
            if call_stage == 'match_missing' and record['matching_supplement']['matched_pairs'] == 0:
                raise PilotError('Zusatzabgleich ohne neue robuste Bildverbindungen; vor weiterer Rekonstruktion gestoppt. Kennzahlen kopieren.')
            if stage == 'extract_metadata':
                _require_engine_gps(workspace, expected)
                if modality == 'thermal':
                    require_thermal_metadata(workspace, expected)
            if stage == 'reconstruct':
                summary = reconstruction_summary(workspace / 'reconstruction.json', expected)
                record.update(summary)
                save()
                if not summary['registration_complete']:
                    raise PilotError('OpenSfM: kein einzelner vollstaendiger Kameraverbund; '
                                     'vor der dichteren Rechnung gestoppt. Kennzahlen dieses Laufs kopieren.')
                if modality == 'thermal':
                    require_thermal_geometry(workspace, expected)
        for source, signature in sources:
            stat = source.stat()
            if (stat.st_size, stat.st_mtime_ns, stat.st_ino) != signature:
                raise PilotError('RGB-Originalquelle waehrend des Piloten veraendert; kein Ergebnis uebernehmen.')
        if inputs_unchanged is not None and not inputs_unchanged():
            raise PilotError('Projekteingaben waehrend des Piloten veraendert; kein Ergebnis uebernehmen.')
        if stopped():
            raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
        ortho, record['raster'] = _inspect_visual_geotiff(workspace, stopped, modality=modality)
        if modality == 'thermal':
            verify_thermal_working_copies(workspace, stopped)
        record.update(status='finished', orthophoto_created=True, thermal_created=modality == 'thermal')
        save()
        return pilot_result(workspace, ortho, len(frames), record['registered_images'], modality)
    except BaseException as error:
        record['status'] = 'cancelled' if isinstance(error, (PilotCancelled, KeyboardInterrupt)) else 'failed'
        save()
        raise


def verify_thermal_working_copies(workspace, stopped):
    mapping = _json(workspace / 'input-map.json')
    if not isinstance(mapping, list) or not 3 <= len(mapping) <= 300 or any(not isinstance(item, dict) for item in mapping):
        raise PilotError('Thermal-Arbeitszuordnung fehlt oder ist ungueltig.')
    for item in mapping:
        if stopped():
            raise PilotCancelled('Thermal-Pilot abgebrochen.')
        name = item.get('working_name')
        if not isinstance(name, str) or not re.fullmatch(r'[0-9]{6}[.]JPG', name):
            raise PilotError('Thermal-Arbeitszuordnung ungueltig.')
        with _regular(workspace / 'images' / name).open('rb') as stream:
            actual = file_digest(stream, 'sha256').hexdigest()
        if actual != str(item.get('content_sha256')).casefold():
            raise PilotError('Thermal-Arbeitskopie veraendert; Rohwerterhalt nicht bestaetigt.')


def run_opensfm_rgb_pilot(frames, config, **kwargs):
    if config.modality != 'rgb':
        raise PilotError('Thermal ueber den getrennten Thermal-Start aufrufen.')
    return _run_opensfm_pilot(frames, config, **kwargs)


def run_opensfm_thermal_pilot(frames, config, **kwargs):
    if config.modality != 'thermal':
        raise PilotError('Thermal-Konfiguration erforderlich.')
    return _run_opensfm_pilot(frames, config, **kwargs)
