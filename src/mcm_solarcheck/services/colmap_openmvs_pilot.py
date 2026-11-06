"""Explicit local RGB pilot using existing COLMAP/OpenMVS executables.

No Qt, network, installer, reconstruction or project writes live here. The
read-only SQLite adapter is separate from the job API so a later server worker
can supply authorized inputs and its own private workspace in the same API.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from hashlib import file_digest, sha256
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time

from mcm_solarcheck.services.micmac_orthophotos import (
    MicMacCancelled, MicMacError, _copy_source, _projected_crs, _stop_process,
)


class PilotError(RuntimeError):
    """Only fixed stage descriptions, never raw tool output or coordinates."""


class PilotCancelled(PilotError):
    pass


class PilotTimeout(PilotError):
    pass


class PilotProcessExit(PilotError):
    def __init__(self, returncode):
        self.returncode = int(returncode)
        super().__init__('Externes Werkzeug meldet einen Fehler.')


@dataclass(frozen=True)
class RgbPilotFrame:
    frame_id: str
    source_file: str
    latitude: float
    longitude: float
    altitude_m: float
    content_sha256: str | None = None


@dataclass(frozen=True)
class RgbPilotConfig:
    colmap: Path
    openmvs: Path
    output_parent: Path
    use_gpu: bool = True
    threads: int = min(8, os.cpu_count() or 1)
    orthomap_resolution: int = 8192
    target_crs: str | None = None
    # RANSAC rejection distance, NOT a measured GNSS accuracy or RTK weight.
    alignment_max_error_m: float = 3.0
    stage_timeout_seconds: float = 86400
    resume_job: Path | None = None


@dataclass(frozen=True)
class RgbPilotResult:
    workspace: Path
    rgb_geotiff: Path
    crs: str
    input_signature: str


def project_choices(database):
    with closing(sqlite3.connect(Path(database).resolve(strict=True).as_uri() + '?mode=ro', uri=True)) as db:
        return tuple(db.execute('SELECT project_id,name FROM projects ORDER BY name,project_id'))


def read_rgb_project(database, project_id):
    """Read the already imported RGB records; no schema migration or EXIF scan."""
    database = Path(database).resolve(strict=True)
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        if db.execute('SELECT 1 FROM projects WHERE project_id=?', (project_id,)).fetchone() is None:
            raise PilotError('Ausgewaehltes Projekt fehlt.')
        rows = db.execute(
            'SELECT f.frame_id,f.source_file,f.latitude,f.longitude,f.altitude_m,t.content_sha256 '
            'FROM image_frames f LEFT JOIN training_samples t '
            "ON t.project_id=f.project_id AND t.source_frame_id=f.frame_id AND t.modality='rgb' "
            'WHERE f.project_id=? ORDER BY f.frame_id', (project_id,),
        ).fetchall()
    result = []
    for row in rows:
        values = dict(row)
        source = Path(values['source_file'])
        values['source_file'] = str(source if source.is_absolute() else database.parent / source)
        result.append(RgbPilotFrame(**values))
    return tuple(result)


def input_signature(frames):
    return sha256(json.dumps([asdict(f) for f in frames], sort_keys=True).encode()).hexdigest()


def _cancel(cancel):
    if cancel():
        raise PilotCancelled('RGB-Pilot abgebrochen; kein Ergebnis uebernommen.')


def _regular(path):
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise PilotError('Erforderliche lokale Datei fehlt oder ist eine Verknuepfung.')
    return path.resolve(strict=True)


def _execute(executable, args, folder, log, cancel, *, allowed=(0,), timeout=86400):
    """Owned process tree; raw output stays in the fresh private job directory."""
    _cancel(cancel)
    env = os.environ.copy()
    env['PATH'] = str(executable.parent) + os.pathsep + env.get('PATH', '')
    env['PROJ_NETWORK'] = 'OFF'
    plugins = executable.parent.parent / 'plugins'
    if plugins.is_dir():
        env['QT_PLUGIN_PATH'] = str(plugins)
        env['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugins / 'platforms')
    flags = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
             if os.name == 'nt' else {'start_new_session': True})
    with log.open('xb') as stream:
        process = subprocess.Popen([str(executable), *map(str, args)], cwd=folder, env=env,
                                   stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, **flags)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                _cancel(cancel)
                if time.monotonic() >= deadline:
                    raise PilotTimeout('Zeitlimit der lokalen Rechenstufe erreicht.')
                try:
                    process.wait(timeout=.15)
                except subprocess.TimeoutExpired:
                    pass
            _cancel(cancel)
            if process.returncode not in allowed:
                raise PilotProcessExit(process.returncode)
        finally:
            if process.poll() is None:
                _stop_process(process)


def _registered_names(path):
    names, pose = set(), True
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('#'):
                continue
            if pose:
                if not line.strip():
                    continue
                fields = line.split(maxsplit=9)
                if len(fields) != 10 or fields[9].strip() in names:
                    raise PilotError('COLMAP-Bildliste ungueltig.')
                names.add(fields[9].strip())
            pose = not pose
    if not pose:
        raise PilotError('COLMAP-Bildliste unvollstaendig.')
    return names


def _read_help_output(paths):
    """Read only bounded outputs belonging to this explicit preflight call."""
    chunks, total = [], 0
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise PilotError('Versionsprotokoll fehlt oder ist eine Verknuepfung.')
        total += path.stat().st_size
        if total > 2 * 1024 * 1024:
            raise PilotError('Werkzeug-Hilfe unerwartet gross.')
        data = path.read_bytes()
        encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        chunks.append(data.decode(encoding, errors='replace'))
    return '\n'.join(chunks)


def _openmvs_versions(text):
    # Util::LogBuild in OpenMVS 2.4 prints "OpenMVS x64 v2.4.0".
    # Parse version records, not directory names or unlabelled numbers.
    records = re.findall(r'\bOpenMVS\s+(?:x(?:32|64)\s+)?v([0-9]{1,3})\.([0-9]{1,3})'
                         r'(?:\.([0-9]{1,3}))?(?![\d.])', text)
    return {(int(major), int(minor), int(patch or 0)) for major, minor, patch in records}


def _resume_inputs(folder, frames):
    """Bind an explicitly selected stopped matching job to the current inputs."""
    folder = Path(folder)
    try:
        record = json.loads(_regular(folder / 'job.json').read_text(encoding='utf-8'))
        mapping = json.loads(_regular(folder / 'input-map.json').read_text(encoding='utf-8'))
        cache = _regular(folder / 'features.db')
        steps = record['steps']
        if (record['status'] not in ('failed', 'cancelled')
                or record['input_signature'] != input_signature(frames)
                or record['rgb_images'] != len(frames)
                or not steps or steps[-1]['stage'] != 'COLMAP-Bildabgleich'
                or steps[-1]['status'] not in ('failed', 'cancelled')
                or not any(s['stage'] == 'COLMAP-Merkmale' and s['status'] in ('finished', 'reused') for s in steps)
                or any(s['status'] not in ('finished', 'reused') for s in steps[:-1])
                or not isinstance(mapping, list) or len(mapping) != len(frames)):
            raise ValueError
        digests = []
        for index, (item, frame) in enumerate(zip(mapping, frames), 1):
            digest = item['content_sha256']
            if (item['working_name'] != f'{index:06d}.JPG'
                    or item['frame_id'] != frame.frame_id or item['source_file'] != frame.source_file
                    or not isinstance(digest, str) or not re.fullmatch('[0-9a-fA-F]{64}', digest)
                    or (frame.content_sha256 and digest.lower() != frame.content_sha256.lower())):
                raise ValueError
            digests.append(digest.lower())
        return cache, tuple(digests)
    except (OSError, PilotError, ValueError, TypeError, KeyError, IndexError):
        raise PilotError('Fortsetzung erfordert einen beim Bildabgleich gestoppten RGB-Job '
                         'mit unveraenderten Projekteingaben und vollstaendiger Zuordnung.') from None


def _snapshot_feature_cache(source, destination, expected_names, cancel):
    """SQLite snapshot, including committed WAL pages; never alter the old job."""
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as old:
            old.execute('PRAGMA query_only=ON')
            with closing(sqlite3.connect(destination)) as new:
                old.backup(new, pages=256, progress=lambda *_: _cancel(cancel))
                new.set_progress_handler(lambda: int(cancel()), 1000)
                if new.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise ValueError
                images = dict(new.execute('SELECT image_id,name FROM images'))
                if set(images.values()) != expected_names or len(images) != len(expected_names):
                    raise ValueError
                for table in ('keypoints', 'descriptors'):
                    rows = new.execute(f'SELECT image_id,rows,cols,length(data) FROM {table}').fetchall()
                    if {r[0] for r in rows} != set(images) or len(rows) != len(images):
                        raise ValueError
                    for _, count, cols, size in rows:
                        if (not isinstance(count, int) or count <= 0
                                or cols not in ((2, 4, 6) if table == 'keypoints' else (128,))
                                or size != count * cols * (4 if table == 'keypoints' else 1)):
                            raise ValueError
                pairs = new.execute('SELECT count(*) FROM matches m '
                                    'JOIN two_view_geometries g ON m.pair_id=g.pair_id').fetchone()[0]
                if pairs > len(images) * (len(images) - 1) // 2:
                    raise ValueError
                return len(images), pairs
    except (sqlite3.Error, OSError, ValueError, TypeError):
        _cancel(cancel)
        raise PilotError('Merkmalsdatenbank nicht konsistent oder nicht vollstaendig fuer diese RGB-Serie. '
                         'Der alte Job bleibt erhalten; keine Merkmale stillschweigend neu berechnet.') from None


def run_rgb_pilot(frames, config, *, should_cancel=None, on_progress=None, inputs_unchanged=None):
    """Produce one private unverified RGB GeoTIFF; never register a partial pair."""
    import numpy as np
    from mcm_solarcheck.services.openmvs_orthomap import OrthomapFormatError, copy_orthomap_geotiff

    frames = tuple(frames)
    cancel = should_cancel or (lambda: False)
    progress = on_progress or (lambda _: None)
    _cancel(cancel)
    if (len(frames) < 3 or len({f.frame_id for f in frames}) != len(frames)
            or not 1 <= config.threads <= 64 or not 128 <= config.orthomap_resolution <= 16384
            or not math.isfinite(config.alignment_max_error_m) or config.alignment_max_error_m <= 0
            or not math.isfinite(config.stage_timeout_seconds) or not 0 < config.stage_timeout_seconds <= 259200):
        raise PilotError('Mindestens drei verschiedene RGB-Bilder und gueltige Pilotparameter erforderlich.')
    rows = [asdict(frame) for frame in frames]
    try:
        crs, transformer = _projected_crs((rows,), config.target_crs)
    except MicMacError as error:
        raise PilotError(str(error)) from None
    colmap = _regular(config.colmap)
    if colmap.name.lower() not in ('colmap.exe', 'colmap'):
        raise PilotError('Die COLMAP-Programmdatei aus bin auswaehlen, keine BAT-Datei.')
    names = ('InterfaceCOLMAP', 'DensifyPointCloud', 'ReconstructMesh', 'RefineMesh', 'TextureMesh')
    root = Path(config.openmvs)
    tools = None
    for directory in (root, root / 'bin'):
        paths = {name: directory / (name + ('.exe' if os.name == 'nt' else '')) for name in names}
        if all(path.is_file() for path in paths.values()):
            tools = {name: _regular(path) for name, path in paths.items()}
            break
    if tools is None:
        raise PilotError('OpenMVS-Ordner mit allen fuenf Pilotprogrammen auswaehlen.')
    parent = Path(config.output_parent)
    if not parent.is_dir() or any(p.is_symlink() for p in (parent, *parent.parents)):
        raise PilotError('Vorhandenen privaten Ausgabeordner auswaehlen.')
    parent = parent.resolve(strict=True)
    if any((p / '.git').is_file() or (p / '.git' / 'HEAD').is_file() for p in (parent, *parent.parents)):
        raise PilotError('Pilot-Ausgabe darf nicht in einem Git-Checkout liegen.')
    for frame in frames:
        source = Path(frame.source_file)
        if not source.is_absolute():
            raise PilotError('Pilotquellen muessen als absolute lokale Pfade vorliegen.')
        source = _regular(source)
        if source.parent == parent or source.parent in parent.parents or parent in source.parents:
            raise PilotError('Ausgabeordner getrennt von den Originalbildordnern auswaehlen.')
        if source.suffix.lower() not in ('.jpg', '.jpeg'):
            raise PilotError('Dieser RGB-Pilot erwartet importierte JPEG-Originalaufnahmen.')
    world = np.array([(*transformer.transform(f.longitude, f.latitude, errcheck=True), f.altitude_m)
                      for f in frames], dtype='float64')
    if not np.isfinite(world).all() or np.linalg.matrix_rank(world[:, :2] - world[0, :2]) < 2:
        raise PilotError('Kamerapositionen brauchen eine endliche, nicht kollineare Lageverteilung.')
    origin = world.mean(axis=0)
    resume = _resume_inputs(config.resume_job, frames) if config.resume_job is not None else None
    workspace = Path(tempfile.mkdtemp(prefix='rgb-pilot-', dir=parent))
    signature = input_signature(frames)
    record = {'status': 'running', 'input_signature': signature, 'rgb_images': len(frames),
              'crs': crs.to_string(), 'origin_projected': origin.tolist(),
              'settings': {'use_gpu': config.use_gpu, 'threads': config.threads,
                           'orthomap_resolution': config.orthomap_resolution,
                           'alignment_max_error_m': config.alignment_max_error_m,
                           'stage_timeout_seconds': config.stage_timeout_seconds},
              'georeferencing_verified': False, 'temperature_verified': False,
              'thermal_created': False, 'steps': []}

    started = time.monotonic()

    def save():
        record['elapsed_seconds'] = round(time.monotonic() - started, 3)
        temporary = workspace / 'job.next.json'
        temporary.write_text(json.dumps(record, indent=2), encoding='utf-8')
        temporary.replace(workspace / 'job.json')
        # Shareable metrics contain no paths, image names, GPS or private output.
        (workspace / 'laufzeiten.json').write_text(json.dumps(
            {key: record[key] for key in ('status', 'rgb_images', 'elapsed_seconds', 'steps',
                                          'georeferencing_verified', 'thermal_created')}, indent=2), encoding='utf-8')

    def stage(label, executable, args, *, help_check=False, native_log_prefix=None):
        _cancel(cancel)
        native_before = set(workspace.glob(native_log_prefix + '-*.log')) if native_log_prefix else set()
        limit = 60 if help_check else config.stage_timeout_seconds
        detail = f' (Zeitlimit {limit / 3600:g} h)' if not help_check else ''
        if label == 'COLMAP-Bildabgleich' and 'resume' in record:
            detail += f'; {record["resume"]["cached_pairs"]} gespeicherte Paarergebnisse uebernommen'
        progress(label + detail)
        item = {'stage': label, 'status': 'running', 'seconds': None, 'timeout_seconds': limit}
        record['steps'].append(item)
        save()
        start = time.monotonic()
        log = workspace / f'step-{len(record["steps"]):02d}.log'
        try:
            _execute(executable, args, workspace, log, cancel,
                     allowed=(0, 1) if help_check else (0,), timeout=limit)
            item['status'] = 'finished'
        except PilotCancelled:
            item['status'] = 'cancelled'
            raise
        except PilotTimeout:
            item.update(status='failed', failure_kind='timeout')
            duration = f'{limit / 3600:g} Stunden' if limit >= 3600 else f'{limit:g} Sekunden'
            raise PilotTimeout(f'{label}: Zeitlimit nach {duration} erreicht; '
                               f'Arbeitsdateien erhalten. {log.name} lokal pruefen.') from None
        except PilotProcessExit as error:
            item.update(status='failed', failure_kind='process_exit', exit_code=error.returncode)
            raise PilotError(f'{label}: Programm mit Code {error.returncode} beendet; '
                             f'{log.name} lokal pruefen.') from None
        except (PilotError, OSError, subprocess.SubprocessError):
            item['status'] = 'failed'
            raise PilotError(f'{label}: abgebrochen oder fehlgeschlagen; {log.name} lokal pruefen.') from None
        finally:
            item['seconds'] = round(time.monotonic() - start, 3)
            save()
        if help_check:
            # Windows OpenMVS can reopen stdout as CONOUT$ (LogConsole::Open).
            # Its own freshly created app log still contains LogBuild/help.
            # Never accept an old log, another program's log or a prior job.
            native_new = sorted(set(workspace.glob(native_log_prefix + '-*.log')) - native_before) if native_log_prefix else []
            return _read_help_output([log, *native_new])

    save()
    try:
        version = stage('COLMAP-Version', colmap, ('-h',), help_check=True)
        if not re.search(r'\bCOLMAP\s+3\.12\.6(?![\d.])', version):
            raise PilotError('Dieser Pilot erwartet COLMAP 3.12.6; keine automatische Installation.')
        cpu_flags = {}
        for name, executable in tools.items():
            help_text = stage(name + '-Version', executable,
                              ('--help', '--working-folder', str(workspace) + os.sep),
                              help_check=True, native_log_prefix=name)
            versions = _openmvs_versions(help_text)
            if versions != {(2, 4, 0)}:
                if not versions:
                    reason = 'Versionsausgabe nicht erkannt'
                elif len(versions) != 1:
                    reason = 'widerspruechliche Versionsangaben'
                else:
                    reason = 'OpenMVS ' + '.'.join(map(str, next(iter(versions)))) + ' erkannt'
                raise PilotError(f'{name}: {reason}; Pilot unterstuetzt 2.4.0. '
                                 'Lokale Versionsprotokolle im neuen Jobordner pruefen.')
            cpu_flags[name] = ('--cuda-device', '-2') if 'cuda-device' in help_text else ()
        images = workspace / 'images'
        images.mkdir()
        refs, source_signatures, source_map = [], [], []
        for index, (row, xyz) in enumerate(zip(rows, world - origin), 1):
            _cancel(cancel)
            progress(f'RGB-Arbeitskopie {index}/{len(rows)}')
            name = f'{index:06d}.JPG'
            # Sources are absolute; the existing checked copier never needs a DB here.
            try:
                copy_row = {**row, 'content_sha256': resume[1][index - 1]} if resume else row
                source_signatures.append(_copy_source(copy_row, images / name, None, cancel))
            except MicMacCancelled:
                raise PilotCancelled('RGB-Pilot abgebrochen.') from None
            except MicMacError as error:
                raise PilotError(str(error)) from None
            refs.append(name + ' ' + ' '.join(f'{v:.12f}' for v in xyz))
            with (images / name).open('rb') as copied:
                digest = row['content_sha256'] or file_digest(copied, 'sha256').hexdigest()
            source_map.append({'working_name': name, 'frame_id': row['frame_id'],
                               'source_file': row['source_file'], 'content_sha256': digest})
        (workspace / 'references.txt').write_text('\n'.join(refs) + '\n', encoding='ascii')
        (workspace / 'input-map.json').write_text(json.dumps(source_map, indent=2), encoding='utf-8')
        sparse, aligned, text, undistorted = (workspace / n for n in ('sparse', 'aligned', 'model-text', 'undistorted'))
        for folder in (sparse, aligned, text, undistorted):
            folder.mkdir()
        db = workspace / 'features.db'
        if resume:
            progress('Vorhandene Merkmale und Bildpaarergebnisse pruefen und uebernehmen')
            cached = {'stage': 'COLMAP-Merkmale', 'status': 'running', 'seconds': None}
            record['steps'].append(cached)
            cache_start = time.monotonic()
            save()
            try:
                image_count, pair_count = _snapshot_feature_cache(
                    resume[0], db, {f'{i:06d}.JPG' for i in range(1, len(rows) + 1)}, cancel)
                cached.update(status='reused', cached_images=image_count, cached_pairs=pair_count)
                record['resume'] = {'source_job': str(resume[0].parent), 'stage': 'COLMAP-Bildabgleich',
                                    'cached_images': image_count, 'cached_pairs': pair_count}
                progress(f'Fortsetzung: {image_count} Merkmalsaetze, {pair_count} gespeicherte Paarergebnisse')
            except BaseException as error:
                cached['status'] = 'cancelled' if isinstance(error, PilotCancelled) else 'failed'
                raise
            finally:
                cached['seconds'] = round(time.monotonic() - cache_start, 3)
                save()
        else:
            stage('COLMAP-Merkmale', colmap, ('feature_extractor', '--database_path', db, '--image_path', images,
                  '--SiftExtraction.use_gpu', int(config.use_gpu), '--SiftExtraction.num_threads', config.threads,
                  '--SiftExtraction.max_image_size', '2400'))
        stage('COLMAP-Bildabgleich', colmap, ('exhaustive_matcher', '--database_path', db,
              '--SiftMatching.use_gpu', int(config.use_gpu), '--SiftMatching.num_threads', config.threads))
        stage('COLMAP-Kameraloesung', colmap, ('mapper', '--database_path', db, '--image_path', images,
              '--output_path', sparse, '--Mapper.num_threads', config.threads))
        models = [p for p in sparse.iterdir() if p.is_dir() and (p / 'images.bin').is_file()]
        if len(models) != 1:
            raise PilotError('COLMAP hat keine einzelne zusammenhaengende Kameraloesung geliefert.')
        stage('COLMAP-Vollstaendigkeit', colmap, ('model_converter', '--input_path', models[0],
              '--output_path', text, '--output_type', 'TXT'))
        expected = {f'{i:06d}.JPG' for i in range(1, len(rows) + 1)}
        if _registered_names(text / 'images.txt') != expected:
            raise PilotError('Nicht alle RGB-Aufnahmen ausgerichtet; kein Teilbild als Gesamtergebnis ausgeben.')
        stage('COLMAP-Positionsabgleich', colmap, ('model_aligner', '--input_path', models[0],
              '--output_path', aligned, '--ref_images_path', workspace / 'references.txt',
              '--ref_is_gps', '0', '--alignment_type', 'custom',
              '--alignment_max_error', config.alignment_max_error_m,
              '--transform_path', workspace / 'alignment.txt'))
        stage('COLMAP-Entzerrung', colmap, ('image_undistorter', '--image_path', images,
              '--input_path', aligned, '--output_path', undistorted, '--output_type', 'COLMAP'))
        jobs = (
            ('InterfaceCOLMAP', ('--input-file', undistorted, '--output-file', 'scene.mvs')),
            ('DensifyPointCloud', ('scene.mvs', '--output-file', 'dense.mvs', '--resolution-level', '1',
                                   '--normalize-coordinates', '0')),
            ('ReconstructMesh', ('dense.mvs', '--output-file', 'mesh.mvs', '--close-holes', '0')),
            ('RefineMesh', ('mesh.mvs', '--output-file', 'refined.mvs', '--resolution-level', '1', '--close-holes', '0')),
            # First create an actually textured mesh. v2.4.0's early orthomap
            # branch checks !HasTexture(), so requesting projection on the
            # untextured refined mesh would skip necessary texturing.
            ('TextureMesh', ('refined.mvs', '--output-file', 'textured.mvs', '--export-type', 'ply', '--close-holes', '0')),
            ('TextureMesh', ('textured.mvs', '--mesh-file', 'textured.ply', '--output-file', 'ortho.mvs',
                             '--export-type', 'ply', '--close-holes', '0',
                             '--orthographic-image-resolution', config.orthomap_resolution)),
        )
        for name, args in jobs:
            label = ('OpenMVS-Orthobild' if args[0] == 'textured.mvs' else 'OpenMVS-Textur') if name == 'TextureMesh' else name
            stage(label, tools[name], (*args, '--working-folder', str(workspace) + os.sep,
                                     '--max-threads', config.threads, *cpu_flags[name],
                                     *(('--archive-type', '2') if name != 'InterfaceCOLMAP' else ())))
        _cancel(cancel)
        progress('Vorhandene OpenMVS-Orthomap als GeoTIFF uebernehmen')
        partial = workspace / 'rgb_ortho.partial.tif'
        try:
            geometry = copy_orthomap_geotiff(workspace / 'ortho_orthomap.png', workspace / 'ortho.ply',
                                           partial, crs=crs, origin=origin.tolist(),
                                           resolution=config.orthomap_resolution, checkpoint=lambda: _cancel(cancel))
        except OrthomapFormatError as error:
            raise PilotError('GeoTIFF-Uebernahme: ' + str(error)) from None
        _cancel(cancel)
        if inputs_unchanged is not None and not inputs_unchanged():
            raise PilotError('Projekteingaben geaendert; kein Ergebnis uebernehmen.')
        for source, expected_stat in source_signatures:
            current = source.stat()
            if (current.st_size, current.st_mtime_ns, current.st_ino) != expected_stat:
                raise PilotError('Originalquelle waehrend des Piloten geaendert.')
        record['raster_reference'] = geometry
        result = workspace / 'rgb_ortho.tif'
        partial.replace(result)
        record['status'] = 'rgb_ready_unverified'
        save()
        return RgbPilotResult(workspace, result, crs.to_string(), signature)
    except BaseException as error:
        record['status'] = 'cancelled' if isinstance(error, (PilotCancelled, KeyboardInterrupt)) or cancel() else 'failed'
        save()
        raise
