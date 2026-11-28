"""One bounded native pair supplement in a fresh copy of a stopped Thermal job."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
import time

from .colmap_openmvs_pilot import PilotError, PilotCancelled, ThermalPilotFrame, _regular
from .opensfm_rgb_pilot import (
    PROFILE, STAGES, _json, _run_opensfm_pilot, read_opensfm_metrics,
    require_thermal_metadata, image_count,
)
from .opensfm_dense_continuation import _exclusive_job

MARKER = '.solarcheck-sparse-bridge.json'
COUNTS = ('target_images', 'candidate_pairs', 'previous_pairs_skipped', 'new_pairs', 'matched_pairs')


def supplement_metrics(data):
    if (not isinstance(data, dict) or data.get('status') not in ('pending', 'finished')
            or any(type(data.get(k)) is not int or not 0 <= data[k] <= 6000 for k in COUNTS)
            or not 1 <= data['target_images'] <= 20
            or data['candidate_pairs'] != data['new_pairs'] + data['previous_pairs_skipped']
            or data['matched_pairs'] > data['new_pairs']):
        raise PilotError('Ungueltiger Zusatzabgleich-Bericht.')
    return {k: data[k] for k in ('status', *COUNTS)}


def can_bridge(report):
    detail = report.get('reconstruction_details', {})
    components = detail.get('components', [])
    count = image_count(report)
    return (report.get('pipeline') == 'opensfm_thermal' and report.get('status') == 'failed'
        and report.get('registration_complete') is False and not report.get('matching_supplement')
        and len(report.get('steps', [])) == 5
        and all(s.get('stage') == STAGES[i] and s.get('status') == 'finished'
                for i, s in enumerate(report['steps']))
        and detail.get('status') == 'completed' and 1 < len(components) <= 20
        and type(count) is int and 3 <= count <= 300
        and report.get('radiometric_sources_preserved') == count
        and max(c['images'] for c in components) >= .8 * count
        and 1 <= count - max(c['images'] for c in components) <= 20)


class _Reuse:
    def __init__(self, source, targets, files):
        self.source, self.targets, self.files = source, targets, files
        self.next_check = 0
        self.stamps = {p: (p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ino) for p in files}

    def unchanged(self, force=False):
        if not force and time.monotonic() < self.next_check:
            return True
        self.next_check = time.monotonic() + 1
        for path, stamp in self.stamps.items():
            current = _regular(path).stat()
            if stamp != (current.st_size, current.st_mtime_ns, current.st_ino):
                raise PilotError('Gespeicherte Ausgangsdaten veraendert; Zusatzabgleich gestoppt.')
        return True

    def prepare(self, workspace, stopped):
        # Copy cache files through an owned byte stream, never links/hardlinks.
        for source in self.files:
            relative = source.relative_to(self.source)
            if relative.parts[0] not in ('exif', 'features', 'matches') and relative.as_posix() not in (
                    'camera_models.json', 'reference_lla.json'):
                continue
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = sha256()
            with source.open('rb') as incoming, target.open('xb') as outgoing:
                while block := incoming.read(1024 * 1024):
                    if stopped():
                        raise PilotCancelled('Zusatzabgleich abgebrochen.')
                    digest.update(block)
                    outgoing.write(block)
            check = sha256()
            with target.open('rb') as incoming:
                while block := incoming.read(1024 * 1024):
                    if stopped():
                        raise PilotCancelled('Zusatzabgleich abgebrochen.')
                    check.update(block)
            if check.digest() != digest.digest():
                raise PilotError('Cachekopie unvollstaendig.')
        self.unchanged(force=True)


def run_sparse_bridge(source, config, *, should_cancel=None, on_progress=None, on_workspace=None, executor=None):
    source = Path(source)
    if (not source.is_absolute() or any(p.is_symlink() for p in (source, *source.parents))
            or any((p / '.git').is_file() or (p / '.git/HEAD').is_file() for p in (source, *source.parents))
            or config.modality != 'thermal'):
        raise PilotError('Privaten gestoppten Thermal-Lauf ausserhalb Git auswaehlen.')
    cancel = should_cancel or (lambda: False)
    if cancel():
        raise PilotCancelled('Zusatzabgleich abgebrochen.')
    with _exclusive_job(source):
        report = read_opensfm_metrics(source)
        manifest = _json(source / 'job.json')
        if (not can_bridge(report) or manifest.get('profile') != PROFILE
                or _json(source / 'config.yaml') != PROFILE or (source / MARKER).exists()):
            raise PilotError('Zusatzabgleich nur einmal fuer einen gescheiterten Thermal-Verbund mit grossem Hauptmodell.')
        mapping = _json(source / 'input-map.json')
        names = [item['working_name'] for item in mapping]
        if names != [f'{i:06d}.JPG' for i in range(1, len(mapping) + 1)]:
            raise PilotError('Gespeicherte Arbeitsreihenfolge ungueltig.')
        models = _json(source / 'reconstruction.json')
        largest = max(models, key=lambda m: len(m['shots']))
        targets = sorted(set(names) - set(largest['shots']))
        require_thermal_metadata(source, set(names))
        frames = []
        for item in mapping:
            name = item['working_name']
            exif = _json(source / 'exif' / (name + '.exif'))
            gps = exif.get('gps', {})
            digest = item.get('content_sha256')
            if not isinstance(digest, str) or not re.fullmatch('[a-fA-F0-9]{64}', digest):
                raise PilotError('Gespeicherte Pruefsumme fehlt; kein neues Originalinventar starten.')
            frames.append(ThermalPilotFrame(item['frame_id'], str(source / 'images' / name),
                gps.get('latitude'), gps.get('longitude'), gps.get('altitude'), digest))
            if not any((source / 'features' / (name + suffix)).is_file() for suffix in ('.features.npz', '.npz')):
                raise PilotError('Gespeicherte Merkmale fehlen; keine Neuberechnung starten.')
        files = [_regular(source / n) for n in ('job.json', 'input-map.json', 'config.yaml',
                                                'reconstruction.json', 'camera_models.json')]
        if (source / 'reference_lla.json').exists():
            files.append(_regular(source / 'reference_lla.json'))
        for directory in ('images', 'exif', 'features', 'matches'):
            root = source / directory
            if not root.is_dir() or root.is_symlink():
                raise PilotError('Gespeicherte Arbeitsdaten fehlen oder sind verknuepft.')
            for path in root.rglob('*'):
                if path.is_symlink():
                    raise PilotError('Gespeicherte Arbeitsdaten duerfen keine Verknuepfungen sein.')
                if path.is_file():
                    files.append(_regular(path))
                if len(files) > 20000:
                    raise PilotError('Arbeitsdaten fuer diesen begrenzten Versuch zu gross.')
        reuse = _Reuse(source, targets, files)
        if shutil.disk_usage(source.parent).free < sum(p.stat().st_size for p in files) * 2 + 512 * 1024 * 1024:
            raise PilotError('Zu wenig Platz fuer getrennte Arbeits-/Cachekopien.')
        # A sibling container keeps copied inputs separate from the new output.
        container = Path(tempfile.mkdtemp(prefix='sparse-bridge-', dir=source.parent))
        with (source / MARKER).open('x', encoding='utf-8') as stream:
            json.dump({'workspace_parent': str(container), 'source_run_id': report.get('run_id')}, stream)
        def checked_cancel():
            reuse.unchanged()
            return cancel()
        bridge_config = replace(config, output_parent=container, project_label=manifest.get('project_label', 'Projekt'))
        return _run_opensfm_pilot(frames, bridge_config, should_cancel=checked_cancel,
            on_progress=on_progress, on_workspace=on_workspace, inputs_unchanged=lambda: reuse.unchanged(force=True),
            executor=executor, _reuse=reuse)
