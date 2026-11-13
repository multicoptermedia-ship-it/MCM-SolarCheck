"""Continue the installed standard dense stages in an existing private job."""
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time

from .colmap_openmvs_pilot import PilotCancelled, PilotError, PilotProcessExit, PilotTimeout, _execute, _regular
from .opensfm_rgb_pilot import (
    LABELS, PROFILE, STAGES, _cache_result,
    _inspect_visual_geotiff, _json, _stored_depthmaps, check_opensfm_depthmap_cache,
    read_opensfm_cache_metrics, reconstruction_summary, report_modality, image_count,
    pilot_result, verify_thermal_working_copies, require_thermal_metadata, require_thermal_geometry,
)

CHECK = 'solarcheck-opensfm-dense-continuation-1'
NAME = r'dense-resume-[0-9]{8}_[0-9]{6}-[a-z0-9_]{8}'
TOTAL_LIMIT = 10800
STAGE_LIMITS = {'compute_depthmaps': 7200, 'fuse_depthmaps': 3600, 'dense_merging': 3600}
SAFE_KEYS = ('check', 'run_id', 'continuation_id', 'started_at', 'status', 'elapsed_seconds',
             'total_timeout_seconds', 'steps', 'cache_before', 'stored_depthmaps',
             'reused_initial_stages', 'orthophoto_created', 'georeferencing_verified',
             'temperature_verified', 'thermal_created')
PROTECTED_METADATA = ('job.json', 'config.yaml', 'input-map.json', 'reconstruction.json',
    'undistorted/reconstruction.json', 'undistorted/tracks.csv',
    'undistorted/undistorted_shot_ids.json', 'undistorted/clusters.json',
    'undistorted/clusters_points.json', 'undistorted/neighbors_best.json',
    'undistorted/neighbors_all.json', 'undistorted/depth_ranges.json')


def _latest(workspace):
    paths = [_regular(p / 'continuation.json') for p in Path(workspace).glob('dense-resume-*')
             if re.fullmatch(NAME, p.name) and (p / 'continuation.json').is_file()]
    return max(paths, key=lambda p: p.stat().st_mtime_ns) if paths else None


def _public(record, initial):
    if (not isinstance(record, dict) or record.get('check') != CHECK
            or record.get('run_id') != initial.get('run_id')
            or not re.fullmatch(NAME, str(record.get('continuation_id')))
            or record.get('status') not in ('running', 'finished', 'failed', 'cancelled')
            or record.get('georeferencing_verified') is not False
            or record.get('temperature_verified') is not False
            or record.get('thermal_created') is not (report_modality(initial) == 'thermal' and record.get('status') == 'finished')
            or type(record.get('orthophoto_created')) is not bool
            or record.get('reused_initial_stages') != 7):
        raise PilotError('Ungueltiger OpenSfM-Fortsetzungsbericht.')
    try:
        datetime.fromisoformat(record['started_at'])
    except (KeyError, TypeError, ValueError):
        raise PilotError('Ungueltige Fortsetzungszeit.') from None
    value = record.get('elapsed_seconds')
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise PilotError('Ungueltige Fortsetzungsdauer.')
    steps = record.get('steps')
    if not isinstance(steps, list) or len(steps) > 3:
        raise PilotError('Ungueltige Fortsetzungsstufen.')
    safe_steps = []
    for index, item in enumerate(steps):
        if (not isinstance(item, dict) or item.get('stage') != STAGES[index + 7]
                or item.get('status') not in ('running', 'finished', 'failed', 'cancelled')):
            raise PilotError('Ungueltige Fortsetzungsstufen.')
        for key in ('seconds', 'timeout_seconds', 'exit_code'):
            v = item.get(key)
            if v is not None and (type(v) not in (int, float) or not math.isfinite(v)):
                raise PilotError('Ungueltige Fortsetzungskennzahl.')
        if item.get('failure_kind') not in (None, 'timeout', 'process_exit'):
            raise PilotError('Ungueltiger Fortsetzungsfehler.')
        safe_steps.append({k: item[k] for k in ('stage', 'status', 'seconds', 'timeout_seconds',
                                               'failure_kind', 'exit_code') if k in item})
    if (record['orthophoto_created'] != (record['status'] == 'finished')
            or (record['status'] == 'finished' and (len(steps) != 3 or any(s['status'] != 'finished' for s in steps)))):
        raise PilotError('Fortsetzungsabschluss ohne vollstaendige Standardstufen ungueltig.')
    safe = {k: record[k] for k in SAFE_KEYS if k in record}
    safe['steps'] = safe_steps
    if 'cache_before' in safe:
        safe['cache_before'] = _cache_result(safe['cache_before'])
    counts = safe.get('stored_depthmaps', {})
    if any(type(counts.get(k)) is not int or counts[k] < 0 for k in ('raw', 'clean')):
        raise PilotError('Ungueltige Tiefenkartenzahl.')
    safe['stored_depthmaps'] = {k: counts[k] for k in ('raw', 'clean')}
    safe['total_timeout_seconds'] = TOTAL_LIMIT
    return safe


def read_opensfm_run_metrics(workspace):
    report = read_opensfm_cache_metrics(workspace)
    latest = _latest(workspace)
    if latest:
        report['dense_continuation'] = _public(_json(latest), report)
    return report


def can_continue_opensfm(report):
    cache = report.get('depthmap_cache_check', {})
    return (report.get('status') in ('failed', 'cancelled') and report.get('registration_complete') is True
        and report.get('dense_continuation', {}).get('status') != 'finished'
        and cache.get('status') == 'completed' and cache.get('changed_during_check') is False
        and cache.get('raw_unreadable') == cache.get('clean_unreadable') == cache.get('foreign_cache_files') == 0
        and cache.get('working_images') == cache.get('clustered_images') == image_count(report)
        and cache.get('clusters_fully_cached', 0) > 0)


@contextmanager
def _exclusive_job(workspace):
    """OS-owned lock releases even on process death; no stale PID-file repair."""
    path = workspace / '.solarcheck-dense.lock'
    if path.is_symlink():
        raise PilotError('Fortsetzungssperre darf keine Verknuepfung sein.')
    if path.exists():
        _regular(path)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise PilotError('Dieser Lauf wird bereits fortgesetzt; vorhandenen Dialog verwenden.') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _digest(path, stopped):
    path = _regular(path)
    stat = path.stat()
    stamp = (stat.st_size, stat.st_mtime_ns, stat.st_ino)
    digest = sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if stopped():
                raise PilotCancelled('Fortsetzung abgebrochen.')
            digest.update(block)
    now = path.stat()
    if stamp != (now.st_size, now.st_mtime_ns, now.st_ino):
        raise PilotError('Gespeicherte Arbeitsdatei wurde veraendert; Fortsetzung gestoppt.')
    return digest.hexdigest(), stamp


def _protected_inputs(workspace, stopped):
    signatures = {}
    for name in PROTECTED_METADATA:
        signatures[name] = _digest(workspace / name, stopped)
    mapping = _json(workspace / 'input-map.json')
    expected = set()
    if not isinstance(mapping, list) or not 3 <= len(mapping) <= 300:
        raise PilotError('Gespeicherte Bild-Arbeitszuordnung fehlt.')
    is_thermal = report_modality(_json(workspace / 'job.json')) == 'thermal'
    for item in mapping:
        name = item.get('working_name') if isinstance(item, dict) else None
        if not isinstance(name, str) or not re.fullmatch(r'[0-9]{6}[.]JPG', name) or name in expected:
            raise PilotError('Gespeicherte Bild-Arbeitszuordnung ungueltig.')
        expected.add(name)
        relative = 'images/' + name
        signatures[relative] = _digest(workspace / relative, stopped)
        if is_thermal:
            signatures['exif/' + name + '.exif'] = _digest(workspace / 'exif' / (name + '.exif'), stopped)
        expected_digest = item.get('content_sha256')
        if (not isinstance(expected_digest, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', expected_digest)
                or signatures[relative][0] != expected_digest.casefold()):
            raise PilotError('Bild-Arbeitskopie weicht von gespeicherter Import-Pruefsumme ab.')
    summary = reconstruction_summary(workspace / 'reconstruction.json', expected)
    if not summary['registration_complete']:
        raise PilotError('Gespeicherter Kameraverbund ist nicht mehr vollstaendig.')
    undistorted = _json(workspace / 'undistorted/undistorted_shot_ids.json')
    if not isinstance(undistorted, dict) or set(undistorted) != expected:
        raise PilotError('Entzerrte Bildzuordnung passt nicht mehr zum Kameraverbund.')
    for values in undistorted.values():
        if (not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], str)
                or values[0] in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', values[0])):
            raise PilotError('Entzerrte Bildzuordnung ungueltig.')
        name = 'undistorted/images/' + values[0]
        signatures[name] = _digest(workspace / name, stopped)
    return signatures


def run_opensfm_dense_continuation(workspace, config, *, should_cancel=None, on_progress=None, executor=None):
    workspace = Path(workspace)
    report = read_opensfm_run_metrics(workspace)
    if config.modality != report_modality(report):
        raise PilotError('RGB- und Thermal-Lauf getrennt waehlen.')
    if not can_continue_opensfm(report):
        raise PilotError('Vorher erfolgreiche Tiefenkartenpruefung dieses gestoppten Laufs laden.')
    if (not workspace.is_absolute() or any(p.is_symlink() for p in (workspace, *workspace.parents))
            or any((p / '.git').is_file() or (p / '.git/HEAD').is_file() for p in (workspace, *workspace.parents))
            or _json(workspace / 'config.yaml') != PROFILE):
        raise PilotError('Privaten bestehenden OpenSfM-Lauf mit unveraendertem Profil verwenden.')
    execute = executor or _execute
    cancel = should_cancel or (lambda: False)
    progress = on_progress or (lambda text: None)
    started = time.monotonic()
    deadline = started + TOTAL_LIMIT
    def stopped():
        if time.monotonic() >= deadline:
            raise PilotTimeout('Drei-Stunden-Gesamtlimit der Fortsetzung erreicht.')
        return cancel()
    with _exclusive_job(workspace):
        report = read_opensfm_run_metrics(workspace)
        if not can_continue_opensfm(report):
            raise PilotError('Fortsetzung inzwischen abgeschlossen oder Cachepruefung nicht mehr verwendbar.')
        previous = _latest(workspace)
        prior_digests = _json(previous).get('protected_digests') if previous else None
        when = datetime.now().astimezone()
        attempt = Path(tempfile.mkdtemp(prefix='dense-resume-' + when.strftime('%Y%m%d_%H%M%S') + '-', dir=workspace))
        record = dict(check=CHECK, run_id=report.get('run_id'), continuation_id=attempt.name,
            started_at=when.isoformat(timespec='seconds'), status='running', elapsed_seconds=0,
            total_timeout_seconds=TOTAL_LIMIT, steps=[], reused_initial_stages=7,
            orthophoto_created=False, georeferencing_verified=False, temperature_verified=False, thermal_created=False)
        if prior_digests is not None:
            record['protected_digests'] = prior_digests
        def save():
            record.update(elapsed_seconds=round(time.monotonic() - started, 3), stored_depthmaps=_stored_depthmaps(workspace))
            for name, data in (('continuation', record), ('Kennzahlen', _public(record, report))):
                temporary = attempt / (name + '.next.json')
                temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
                temporary.replace(attempt / (name + '.json'))
        save()
        try:
            progress('Fortsetzung: gespeicherte Arbeitsdateien pruefen; keine Original-/Projektdateien.')
            signatures = _protected_inputs(workspace, stopped)
            if report_modality(report) == 'thermal':
                names = {item['working_name'] for item in _json(workspace / 'input-map.json')}
                require_thermal_metadata(workspace, names)
                require_thermal_geometry(workspace, names)
            digests = {k: v[0] for k, v in signatures.items()}
            if prior_digests is not None and prior_digests != digests:
                raise PilotError('Geschuetzte Eingaben seit vorheriger Fortsetzung veraendert.')
            record['protected_digests'] = digests
            save()
            progress('Fortsetzung: vorhandene Tiefenkarten vor dem Rechnen erneut lesen (max. zehn Minuten).')
            checked = check_opensfm_depthmap_cache(workspace, config, should_cancel=stopped, executor=execute)
            if not can_continue_opensfm(checked):
                raise PilotError('Cache vor Fortsetzung nicht unveraendert lesbar; keine Bildstufe gestartet.')
            record['cache_before'] = checked['depthmap_cache_check']
            save()
            def unchanged():
                for name, (_, stamp) in signatures.items():
                    current = _regular(workspace / name).stat()
                    if stamp != (current.st_size, current.st_mtime_ns, current.st_ino):
                        raise PilotError('Geschuetzte Arbeitsdateien waehrend Fortsetzung veraendert; kein Ergebnis uebernehmen.')
            for index in range(7, 10):
                if stopped():
                    raise PilotCancelled('Fortsetzung abgebrochen.')
                unchanged()
                stage = STAGES[index]
                limit = min(STAGE_LIMITS[stage], deadline - time.monotonic())
                label = LABELS[index].replace('RGB', report_modality(report).upper())
                progress(f'{index + 1}/10 OpenSfM-Fortsetzung: {label} (max. {limit / 60:.0f} min)')
                step = dict(stage=stage, status='running', seconds=None, timeout_seconds=round(limit, 3))
                record['steps'].append(step)
                save()
                tick = time.monotonic()
                log = attempt / f'step-{index + 1:02d}.log'
                args = (*config.engine_command[1:], '-I', str(config.runner), stage, str(workspace))
                if stage == 'dense_merging':
                    args += ('--georeferenced',)
                try:
                    execute(Path(config.engine_command[0]), args, workspace, log, stopped, timeout=limit,
                        env_overrides={'TEMP': str(workspace / 'tmp'), 'TMP': str(workspace / 'tmp'),
                            'MPLCONFIGDIR': str(workspace / 'matplotlib'), 'VSCMD_SKIP_SENDTELEMETRY': '1'})
                    step['status'] = 'finished'
                except PilotProcessExit as error:
                    step.update(status='failed', failure_kind='process_exit', exit_code=error.returncode)
                    raise PilotError(f'OpenSfM-Fortsetzung {LABELS[index].replace('RGB', report_modality(report).upper())}: Code {error.returncode}; {attempt.name}/{log.name} lokal pruefen.') from None
                except PilotTimeout:
                    step.update(status='failed', failure_kind='timeout')
                    raise PilotTimeout(f'OpenSfM-Fortsetzung {LABELS[index].replace('RGB', report_modality(report).upper())}: Zeitlimit erreicht; Arbeitsstand gespeichert.') from None
                except PilotCancelled:
                    step['status'] = 'cancelled'
                    raise
                finally:
                    step['seconds'] = round(time.monotonic() - tick, 3)
                    save()
            unchanged()
            ortho, record['raster'] = _inspect_visual_geotiff(workspace, stopped, modality=report_modality(report))
            if report_modality(report) == 'thermal':
                verify_thermal_working_copies(workspace, stopped)
            record.update(status='finished', orthophoto_created=True, thermal_created=report_modality(report) == 'thermal')
            save()
            return pilot_result(workspace, ortho, image_count(report), report['registered_images'], report_modality(report))
        except BaseException as error:
            record['status'] = 'cancelled' if isinstance(error, (PilotCancelled, KeyboardInterrupt)) else 'failed'
            if record['steps'] and record['steps'][-1]['status'] == 'running':
                record['steps'][-1]['status'] = record['status']
            save()
            raise
