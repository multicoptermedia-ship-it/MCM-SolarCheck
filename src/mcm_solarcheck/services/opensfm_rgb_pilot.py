"""Local job adapter for the qualified OpenSfM engine; no photogrammetry here.

The shared API accepts authorized RGB records. SQLite selection and desktop UI
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
    _execute, _regular, input_signature,
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


@dataclass(frozen=True)
class OpenSfMPilotResult:
    workspace: Path
    rgb_geotiff: Path
    rgb_images: int
    registered_images: int


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
               'thermal_created', 'elapsed_seconds', 'steps', 'stored_depthmaps')


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
    filename = manifest.get('metrics_filename', 'laufzeiten.json')
    if (not isinstance(filename, str) or (filename != 'laufzeiten.json' and not re.fullmatch(
            r'OpenSfM_RGB_[0-9]{8}_[0-9]{6}_[a-z0-9_]{8}_Kennzahlen[.]json', filename))):
        raise PilotError('OpenSfM-Kennzahlendatei hat einen ungueltigen Namen.')
    report = _json(workspace / filename)
    if (not isinstance(report, dict) or report.get('pipeline', 'opensfm_rgb') != 'opensfm_rgb'
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
        for key in ('seconds', 'timeout_seconds', 'exit_code'):
            value = item.get(key)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise PilotError('OpenSfM-Kennzahlen enthalten ungueltige Zahlen.')
        if item.get('failure_kind') not in (None, 'timeout', 'process_exit'):
            raise PilotError('OpenSfM-Kennzahlen enthalten einen unbekannten Fehlerstatus.')
        safe_steps.append({k: item[k] for k in ('stage', 'status', 'seconds', 'timeout_seconds',
                                               'failure_kind', 'exit_code') if k in item})
    safe = {key: report[key] for key in METRIC_KEYS if key in report and key != 'steps'}
    for key in ('rgb_images', 'registered_images', 'models', 'missing_images', 'foreign_images', 'points', 'elapsed_seconds'):
        if key in safe and (type(safe[key]) not in (int, float) or not math.isfinite(safe[key]) or safe[key] < 0):
            raise PilotError('OpenSfM-Kennzahlen enthalten ungueltige Zahlen.')
    for key in ('registration_complete', 'orthophoto_created', 'georeferencing_verified', 'temperature_verified', 'thermal_created'):
        if key in safe and type(safe[key]) is not bool:
            raise PilotError('OpenSfM-Kennzahlen enthalten einen ungueltigen Status.')
    if 'run_id' in safe and not re.fullmatch(r'opensfm-rgb-[0-9]{8}-[0-9]{6}-[a-z0-9_]{8}', str(safe['run_id'])):
        raise PilotError('OpenSfM-Laufkennung ungueltig.')
    if 'started_at' in safe:
        try:
            datetime.fromisoformat(safe['started_at'])
        except (TypeError, ValueError):
            raise PilotError('OpenSfM-Laufdatum ungueltig.') from None
    safe.update(pipeline='opensfm_rgb', steps=safe_steps, stored_depthmaps=_stored_depthmaps(workspace))
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
    return f'OpenSfM RGB · {project} · {stamp}\nOrdner: {workspace.name}'


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
    result = {'models': len(models), 'registered_images': len(names),
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


def _validate_inputs(frames, config):
    if not 3 <= len(frames) <= 300 or len({f.frame_id for f in frames}) != len(frames):
        raise PilotError('Erster Pilot: vollstaendiges zusammengehoeriges Projekt mit 3 bis 300 RGB-JPGs waehlen.')
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
            raise PilotError('Importierte RGB-Quellen muessen absolute lokale Pfade haben.')
        source = _regular(source)
        if (source.suffix.lower() not in ('.jpg', '.jpeg') or source in paths
                or source.parent == parent or source.parent in parent.parents or parent in source.parents):
            raise PilotError('RGB-JPGs und davon getrennten Ausgabeordner waehlen; keine doppelten Quellen.')
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


def run_opensfm_rgb_pilot(frames, config, *, should_cancel=None, on_progress=None,
                          inputs_unchanged=None, executor=None, on_workspace=None):
    """Qualified standard stages -> checked existing GeoTIFF, no project writes."""
    frames = tuple(frames)
    cancel = should_cancel or (lambda: False)
    progress = on_progress or (lambda text: None)
    execute = executor or _execute
    if cancel():
        raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
    parent = _validate_inputs(frames, config)
    began = datetime.now().astimezone()
    stamp = began.strftime('%Y%m%d_%H%M%S')
    label = unicodedata.normalize('NFKD', str(config.project_label)).encode('ascii', 'ignore').decode()
    slug = re.sub('[^A-Za-z0-9]+', '-', label).strip('-')[:32] or 'Projekt'
    workspace = Path(tempfile.mkdtemp(prefix=f'{stamp}_OpenSfM_RGB_{slug}_', dir=parent))
    run_id = f'opensfm-rgb-{stamp.replace("_", "-")}-{workspace.name[-8:]}'
    metrics_filename = f'OpenSfM_RGB_{stamp}_{workspace.name[-8:]}_Kennzahlen.json'
    started = time.monotonic()
    deadline = started + config.total_timeout_seconds
    record = {'status': 'running', 'rgb_images': len(frames), 'registered_images': 0,
              'pipeline': 'opensfm_rgb', 'run_id': run_id, 'started_at': began.isoformat(timespec='seconds'),
              'project_label': str(config.project_label), 'metrics_filename': metrics_filename,
              'models': 0, 'missing_images': len(frames), 'foreign_images': 0, 'points': 0,
              'registration_complete': False, 'orthophoto_created': False,
              'georeferencing_verified': False, 'temperature_verified': False,
              'thermal_created': False, 'steps': [], 'expected_engine_source': ENGINE_SOURCE,
              'input_signature': input_signature(frames), 'profile': PROFILE,
              'stage_timeout_seconds': config.stage_timeout_seconds,
              'total_timeout_seconds': config.total_timeout_seconds}

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
            progress(f'RGB-Arbeitskopien {index}/{len(frames)}')
            name = f'{index:06d}.JPG'
            try:
                sources.append(_copy_source(asdict(frame), images / name, None, stopped))
            except MicMacCancelled:
                raise PilotCancelled('OpenSfM-Pilot abgebrochen.') from None
            except MicMacError:
                raise PilotError('RGB-Arbeitskopie fehlgeschlagen oder Quelle veraendert; Originale bleiben erhalten.') from None
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
        for index, (stage, label) in enumerate(zip(STAGES, LABELS), 1):
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
            arguments = (*config.engine_command[1:], '-I', str(config.runner), stage, str(workspace))
            if stage == 'dense_merging':
                arguments += ('--georeferenced',)
            try:
                execute(Path(config.engine_command[0]), arguments, workspace, log, stopped,
                        timeout=limit, env_overrides=runtime_env)
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
            if stage == 'extract_metadata':
                _require_engine_gps(workspace, expected)
            if stage == 'reconstruct':
                summary = reconstruction_summary(workspace / 'reconstruction.json', expected)
                record.update(summary)
                save()
                if not summary['registration_complete']:
                    raise PilotError('OpenSfM: kein einzelner vollstaendiger RGB-Kameraverbund; '
                                     'vor der dichteren Rechnung gestoppt. Kennzahlen dieses Laufs kopieren.')
        for source, signature in sources:
            stat = source.stat()
            if (stat.st_size, stat.st_mtime_ns, stat.st_ino) != signature:
                raise PilotError('RGB-Originalquelle waehrend des Piloten veraendert; kein Ergebnis uebernehmen.')
        if inputs_unchanged is not None and not inputs_unchanged():
            raise PilotError('Projekteingaben waehrend des Piloten veraendert; kein Ergebnis uebernehmen.')
        if stopped():
            raise PilotCancelled('OpenSfM-Pilot abgebrochen.')
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
            record['raster'] = {'crs': reference.crs, 'width': reference.width, 'height': reference.height}
        except (PilotCancelled, PilotTimeout):
            raise
        except Exception:
            raise PilotError('OpenSfM-Ausgabe ohne verwendbares projiziertes RGB-GeoTIFF; keine CRS-Ergaenzung.') from None
        record.update(status='finished', orthophoto_created=True)
        save()
        return OpenSfMPilotResult(workspace, ortho, len(frames), record['registered_images'])
    except BaseException as error:
        record['status'] = 'cancelled' if isinstance(error, (PilotCancelled, KeyboardInterrupt)) else 'failed'
        save()
        raise
