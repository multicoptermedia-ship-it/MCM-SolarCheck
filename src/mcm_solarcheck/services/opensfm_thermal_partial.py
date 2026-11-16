"""Explicit incomplete visual preview from an existing native Thermal component.

No matching, reconstruction, pose transfer, project registration or temperature conversion.
The full-result gates deliberately remain unchanged.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
import time

from .colmap_openmvs_pilot import PilotError, PilotCancelled, PilotTimeout, _execute, _regular
from .opensfm_dense_continuation import _exclusive_job, _digest
from .opensfm_rgb_pilot import (
    PROFILE, STAGES, _json, read_opensfm_metrics, reconstruction_summary,
    require_thermal_geometry, _inspect_visual_geotiff,
)

NOTICE = ('UNVOLLSTAENDIGE Thermal-Teilvorschau; nur Darstellung, keine Celsiusmatrix. '
          'Keine vollstaendige Abdeckung, Qualitaets- oder Geometriefreigabe.')
MARKER = '.solarcheck-thermal-partial-'
DERIVED_GEOMETRY = ('undistorted/reconstruction.json', 'undistorted/tracks.csv',
    'undistorted/undistorted_shot_ids.json', 'undistorted/clusters.json',
    'undistorted/clusters_points.json', 'undistorted/neighbors_best.json',
    'undistorted/neighbors_all.json', 'undistorted/depth_ranges.json')


def _pointer(source):
    source = Path(source)
    return source.parent / (MARKER + sha256(str(source).encode('utf-8')).hexdigest()[:16] + '.json')


def preview_label(included, total):
    return f'unvollständig: {included} von {total} Bildern'



def can_preview(report):
    return (report.get('pipeline') == 'opensfm_thermal'
            and report.get('status') == 'failed'
            and report.get('registration_complete') is False
            and type(report.get('thermal_images')) is int
            and 3 <= report['thermal_images'] <= 300
            and report.get('radiometric_sources_preserved') == report['thermal_images']
            and len(report.get('steps', [])) >= 5
            and all(s.get('stage') == STAGES[i] and s.get('status') == 'finished'
                    for i, s in enumerate(report['steps'][:5])))


def read_partial_preview(source):
    """Local reopening only; do not include private output paths in shared metrics."""
    marker = _pointer(source)
    if not marker.exists():
        return None
    record = _json(marker)
    folder = Path(record.get('workspace', ''))
    if (not folder.is_absolute() or folder.parent != Path(source).parent
            or not re.fullmatch(r'thermal-partial-[a-z0-9_]{8}', folder.name)
            or any(p.is_symlink() for p in (folder, *folder.parents))):
        raise PilotError('Ungueltiger Teilvorschauordner.')
    result = _json(folder / 'partial-preview.json')
    if (result.get('incomplete') is not True or result.get('temperature_verified') is not False
            or result.get('georeferencing_verified') is not False
            or result.get('status') not in ('running', 'finished', 'failed', 'cancelled')):
        raise PilotError('Ungueltiger Teilvorschaubericht.')
    if (any(type(result.get(k)) is not int for k in ('source_images', 'included_images', 'excluded_images'))
            or not 3 <= result['included_images'] < result['source_images'] <= 300
            or result['excluded_images'] != result['source_images'] - result['included_images']
            or result.get('thermal_created') is not False or result.get('orthophoto_created') is not False):
        raise PilotError('Ungueltige Teilvorschaukennzahlen.')
    safe = {k: result[k] for k in ('status', 'incomplete', 'source_images', 'included_images',
        'excluded_images', 'temperature_verified', 'georeferencing_verified', 'thermal_created', 'orthophoto_created')}
    safe['notice'] = NOTICE
    safe['label'] = preview_label(result['included_images'], result['source_images'])
    steps = result.get('steps')
    if (not isinstance(steps, list) or len(steps) > 5
            or any(not isinstance(s, dict) or s.get('stage') != STAGES[i + 5]
                or s.get('status') not in ('running', 'finished', 'failed', 'cancelled') for i, s in enumerate(steps))
            or result['status'] == 'finished' and (len(steps) != 5 or any(s['status'] != 'finished' for s in steps))):
        raise PilotError('Ungueltige Teilvorschaustufen.')
    safe['steps'] = [{k: s[k] for k in ('stage', 'status')} for s in steps]
    return folder, safe


def run_partial_preview(source, config, *, should_cancel=None, on_progress=None, executor=None):
    source = Path(source)
    if (not source.is_absolute() or config.modality != 'thermal'
            or any(p.is_symlink() for p in (source, *source.parents))
            or any((p / '.git').is_file() or (p / '.git/HEAD').is_file() for p in (source, *source.parents))):
        raise PilotError('Privaten Thermal-Lauf ausserhalb Git waehlen.')
    cancel = should_cancel or (lambda: False)
    progress = on_progress or (lambda text: None)
    execute = executor or _execute
    deadline = time.monotonic() + min(config.total_timeout_seconds, 10800)

    def stopped():
        if time.monotonic() >= deadline:
            raise PilotTimeout('Teilvorschau: Gesamtzeitlimit erreicht.')
        return cancel()

    def check_cancel():
        if stopped():
            raise PilotCancelled('Teilvorschau abgebrochen.')

    with _exclusive_job(source.parent):
        check_cancel()
        initial_signatures = {name: _digest(source / name, stopped) for name in
            ('reconstruction.json', 'input-map.json', 'job.json', 'config.yaml')}
        report = read_opensfm_metrics(source)
        if not can_preview(report) or _json(source / 'config.yaml') != PROFILE:
            raise PilotError('Gespeicherten unvollstaendigen Thermal-Kameraverbund laden.')
        if _pointer(source).exists():
            raise PilotError('Teilvorschau bereits angelegt; vorhandenen Ausgabeordner oeffnen.')
        mapping = _json(source / 'input-map.json')
        if (not isinstance(mapping, list) or len(mapping) != report['thermal_images']
                or any(not isinstance(m, dict) or not re.fullmatch(r'[0-9]{6}[.]JPG', str(m.get('working_name'))) for m in mapping)):
            raise PilotError('Gespeicherte Bildzuordnung ungueltig.')
        expected = {m['working_name'] for m in mapping}
        if len(expected) != len(mapping):
            raise PilotError('Doppelte Bildzuordnung.')
        models = _json(source / 'reconstruction.json')
        reconstruction_summary(source / 'reconstruction.json', expected)
        sizes = [len(m['shots']) for m in models]
        if not sizes or sizes.count(max(sizes)) != 1:
            raise PilotError('Kein eindeutiges Hauptmodell.')
        model = models[sizes.index(max(sizes))]
        selected = set(model['shots'])
        if not selected < expected or not 3 <= len(selected) or len(selected) < .8 * len(expected):
            raise PilotError('Kein begrenztes grosses Thermal-Teilmodell.')
        folder = Path(tempfile.mkdtemp(prefix='thermal-partial-', dir=source.parent))
        record = dict(status='running', incomplete=True, notice=NOTICE,
            source_images=len(expected), included_images=len(selected), excluded_images=len(expected - selected),
            temperature_verified=False, georeferencing_verified=False, thermal_created=False,
            orthophoto_created=False, steps=[])

        record['label'] = preview_label(len(selected), len(expected))

        def save():
            temporary = folder / 'partial-preview.next.json'
            temporary.write_text(json.dumps(record, indent=2), encoding='utf-8')
            temporary.replace(folder / 'partial-preview.json')

        save()
        with _pointer(source).open('x', encoding='utf-8') as stream:
            json.dump({'workspace': str(folder)}, stream)
        try:
            progress(record['label'] + ' · ' + NOTICE)
            signatures = dict(initial_signatures)

            def copy(relative, expected_digest=None):
                check_cancel()
                path = _regular(source / relative)
                if any(p.is_symlink() for p in path.parents):
                    raise PilotError('Arbeitsdateien duerfen keine Verknuepfungen sein.')
                digest, stamp = _digest(path, stopped)
                if expected_digest is not None and digest != expected_digest:
                    raise PilotError('Thermal-Arbeitskopie weicht von gespeicherter Pruefsumme ab.')
                if relative in signatures and signatures[relative] != (digest, stamp):
                    raise PilotError('Ausgangslauf waehrend Vorbereitung veraendert.')
                target = folder / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with path.open('rb') as incoming, target.open('xb') as outgoing:
                    while block := incoming.read(1024 * 1024):
                        check_cancel()
                        outgoing.write(block)
                if _digest(target, stopped)[0] != digest:
                    raise PilotError('Teilvorschaukopie unvollstaendig.')
                signatures[relative] = (digest, stamp)

            # Copy only the selected saved working images and native metadata.
            # No source_file, original archive, raw parser, features or matches are used.
            for item in mapping:
                name = item['working_name']
                if name in selected:
                    digest = item.get('content_sha256')
                    if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
                        raise PilotError('Gespeicherte Pruefsumme fehlt.')
                    copy('images/' + name, digest)
                    copy('exif/' + name + '.exif')
            for name in ('config.yaml', 'camera_models.json', 'reference_lla.json'):
                copy(name)
            (folder / 'reconstruction.json').write_text(json.dumps([model]), encoding='utf-8')
            # Native undistort reads existing tracks; it ignores other components.
            copy('tracks.csv')
            require_thermal_geometry(folder, selected)
            for name in ('tmp', 'matplotlib'):
                (folder / name).mkdir()

            # Private provenance stays outside metrics/clipboard and outside the source.
            excluded = [dict(working_name=item['working_name'], frame_id=item.get('frame_id'),
                source_file=item.get('source_file'), reason='not_in_saved_main_component')
                for item in mapping if item['working_name'] not in selected]
            (folder / 'excluded-images.LOCAL.json').write_text(json.dumps(excluded, indent=2), encoding='utf-8')
            local_names = [name for name in signatures if (folder / name).is_file()]
            local_names.append('reconstruction.json')
            manifest = dict(source={name: value[0] for name, value in signatures.items()},
                working={name: _digest(folder / name, stopped)[0] for name in local_names})
            (folder / 'partial-inputs.LOCAL.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            return _run_stages(source, folder, record, config, stopped, progress, execute)
        except BaseException as error:
            record['status'] = 'cancelled' if isinstance(error, (PilotCancelled, KeyboardInterrupt)) else 'failed'
            if record['steps'] and record['steps'][-1]['status'] == 'running':
                record['steps'][-1]['status'] = record['status']
            save()
            raise



def _save(folder, record):
    temporary = folder / 'partial-preview.next.json'
    temporary.write_text(json.dumps(record, indent=2), encoding='utf-8')
    temporary.replace(folder / 'partial-preview.json')


def _run_stages(source, folder, record, config, stopped, progress, execute):
    manifest = _json(folder / 'partial-inputs.LOCAL.json')

    def unchanged():
        if stopped():
            raise PilotCancelled('Teilvorschau abgebrochen.')
        for root, key in ((source, 'source'), (folder, 'working')):
            values = manifest.get(key)
            if not isinstance(values, dict) or not values:
                raise PilotError('Teilvorschau ohne gespeicherte Eingabepruefsummen.')
            for name, digest in values.items():
                relative = Path(name)
                if relative.is_absolute() or '..' in relative.parts or any(p.is_symlink() for p in (root / relative).parents):
                    raise PilotError('Ungueltige Teilvorschau-Eingabe.')
                if _digest(root / relative, stopped)[0] != digest:
                    raise PilotError('Gespeicherte Eingaben veraendert; Teilvorschau gestoppt.')

    derived_path = folder / 'partial-derived.LOCAL.json'

    def derived_unchanged():
        if not derived_path.exists():
            return
        for name, digest in _json(derived_path).items():
            if name not in DERIVED_GEOMETRY or _digest(folder / name, stopped)[0] != digest:
                raise PilotError('Gespeicherte entzerrte Thermalgeometrie veraendert.')

    try:
        unchanged()
        derived_unchanged()
        selected = set(_json(folder / 'reconstruction.json')[0]['shots'])
        require_thermal_geometry(folder, selected)
        done = 0
        for step in record['steps']:
            if step['status'] != 'finished':
                break
            done += 1
        # If validation/publication failed after merging, regenerate that output only.
        done = min(done, 4)
        record['steps'] = record['steps'][:done]
        record['status'] = 'running'
        _save(folder, record)
        for stage in STAGES[5 + done:]:
            unchanged()
            derived_unchanged()
            step = dict(stage=stage, status='running')
            record['steps'].append(step)
            _save(folder, record)
            progress(record['label'] + ' · ' + NOTICE + ' ' + stage)
            args = (*config.engine_command[1:], '-I', str(config.runner), stage, str(folder))
            if stage == 'dense_merging':
                args += ('--georeferenced',)
            execute(Path(config.engine_command[0]), args, folder, folder / (stage + '.log'), stopped,
                timeout=min(config.stage_timeout_seconds, 3600, config.total_timeout_seconds),
                env_overrides={'TEMP': str(folder / 'tmp'), 'TMP': str(folder / 'tmp'),
                    'MPLCONFIGDIR': str(folder / 'matplotlib'), 'VSCMD_SKIP_SENDTELEMETRY': '1'})
            step['status'] = 'finished'
            if stage in ('undistort', 'dense_clustering'):
                derived = {name: _digest(folder / name, stopped)[0] for name in DERIVED_GEOMETRY
                           if (folder / name).is_file()}
                derived_path.write_text(json.dumps(derived), encoding='utf-8')
            _save(folder, record)
        unchanged()
        derived_unchanged()
        ortho, _ = _inspect_visual_geotiff(folder, stopped, modality='thermal', allow_incomplete_preview=True)
        import rasterio
        with rasterio.open(ortho, 'r+') as raster:
            raster.update_tags(SOLARCHECK_INCOMPLETE='true', SOLARCHECK_PREVIEW_KIND='thermal_partial',
                SOLARCHECK_LABEL=record['label'],
                SOLARCHECK_INCLUDED_IMAGES=str(record['included_images']),
                SOLARCHECK_SOURCE_IMAGES=str(record['source_images']),
                SOLARCHECK_EXCLUDED_IMAGES=str(record['excluded_images']),
                SOLARCHECK_COVERAGE_VERIFIED='false', SOLARCHECK_GEOMETRY_VERIFIED='false',
                SOLARCHECK_TEMPERATURE_VERIFIED='false', SOLARCHECK_PAIR_IMPORT_ALLOWED='false',
                TIFFTAG_IMAGEDESCRIPTION=record['label'] + ' · ' + NOTICE)
        output = ortho.with_name('UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif')
        ortho.replace(output)
        output.with_suffix('.txt').write_text(record['label'] + '\n' + NOTICE, encoding='utf-8')
        unchanged()
        record['status'] = 'finished'
        _save(folder, record)
        return folder, record
    except BaseException as error:
        record['status'] = 'cancelled' if isinstance(error, (PilotCancelled, KeyboardInterrupt)) else 'failed'
        if record['steps'] and record['steps'][-1]['status'] == 'running':
            record['steps'][-1]['status'] = record['status']
        _save(folder, record)
        raise


def continue_partial_preview(source, config, *, should_cancel=None, on_progress=None, executor=None):
    """Resume this preview only, from its first unfinished native dense stage."""
    source = Path(source)
    if (not source.is_absolute() or config.modality != 'thermal'
            or any(p.is_symlink() for p in (source, *source.parents))
            or any((p / '.git').is_file() or (p / '.git/HEAD').is_file() for p in (source, *source.parents))):
        raise PilotError('Privaten Thermal-Lauf ausserhalb Git waehlen.')
    deadline = time.monotonic() + min(config.total_timeout_seconds, 10800)
    cancel = should_cancel or (lambda: False)
    def stopped():
        if time.monotonic() >= deadline:
            raise PilotTimeout('Teilvorschau: Gesamtzeitlimit erreicht.')
        return cancel()
    with _exclusive_job(source.parent):
        loaded = read_partial_preview(source)
        if not loaded or loaded[1]['status'] not in ('failed', 'cancelled'):
            raise PilotError('Nur eine gestoppte Thermal-Teilvorschau fortsetzen.')
        folder, record = loaded
        if not (folder / 'partial-inputs.LOCAL.json').is_file():
            raise PilotError('Vorbereitung unvollstaendig; keine Bildstufe fortsetzen.')
        return _run_stages(source, folder, record, config, stopped,
            on_progress or (lambda text: None), executor or _execute)
