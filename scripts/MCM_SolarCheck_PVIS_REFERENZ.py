"""Explicit public PVIS-10K intake: two pinned archives, no image decoding/training."""
import argparse
from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path
import shutil
import ssl
import stat
import sys
import urllib.error
import urllib.request
import zipfile

sys.path[:0] = [str(Path(__file__).resolve().parent),
                 str(Path(__file__).resolve().parents[1] / 'src')]
from MCM_SolarCheck_CVUT_PAKETPRUEFUNG import (
    atomic_json, checked_member_name, digest, local, package_lock,
)
from mcm_solarcheck.services.pv_dataset_intake import ImageModality, PublicDatasetRecord
from mcm_solarcheck.services.pv_yolo_dataset_validation import validate_dataset_relative_path

CHECK = 'solarcheck-pvis-reference-1'
SOURCE = 'https://zenodo.org/records/23886365'
BASE = SOURCE + '/files/'
MAX_JSON = 40_000_000
DOCUMENTS = {
    'LICENSE.md': (1604, 'e4243384c8be48da18c285ebc6678ff6f60e659a2569be6ca1b7d2a2b209dbf7'),
    'README.md': (4497, '419118c87961a8ee17969a0abd1e347909773d79b86fb8673db2dff22cf71e7b'),
    'archive_manifest.csv': (3644, '72337526118b2cbf62783f7849a94b8f9daee942700c54e00bd392191c08f540'),
}


@dataclass(frozen=True)
class Station:
    split: str
    station: str
    images: int
    annotations: int
    unpacked: int
    size: int
    sha256: str

    @property
    def name(self):
        return f'PVDataset_{self.split}_{self.station}.zip'

    @property
    def prefix(self):
        return f'{self.split}/{self.station}/'


STATIONS = (
    Station('train', '009', 58, 16697, 210225292, 201375386,
            'f9b136c5809f37f1d714c402e642876869955598a9a4db8c3d5909a4ffa6b9fa'),
    Station('test', '024', 84, 20766, 260642818, 251234092,
            '9db6b88c49936e47c74f1c77af24e95cf9807e0558c5ff799c16be402beee420'),
)


def _cancel(should_cancel):
    if should_cancel():
        raise KeyboardInterrupt


def _identity(path, size, expected):
    local(path)
    if not path.is_file() or path.stat().st_size != size or digest(path) != expected:
        raise ValueError('Public archive identity differs from pinned source')


def _receive(target, size, expected, archive_dir, should_cancel):
    """Reuse complete files; restart only the interrupted file, never append bytes."""
    local(target)
    if target.exists():
        _identity(target, size, expected)
        return
    temporary = local(target.with_name(target.name + '.download'))
    try:
        if archive_dir is None:
            source = urllib.request.urlopen(BASE + target.name + '?download=1', timeout=30)
        else:
            source = local(archive_dir / target.name).open('rb')
        with source, temporary.open('wb') as output:
            total = 0
            while True:
                _cancel(should_cancel)
                block = source.read(min(1024**2, size - total + 1))
                if not block:
                    break
                total += len(block)
                if total > size:
                    raise ValueError('Public download larger than pinned size')
                output.write(block)
        _identity(temporary, size, expected)
        _cancel(should_cancel)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _number(value):
    return type(value) in (int, float) and isfinite(value)


def _positive_int(value):
    return type(value) is int and value > 0


def _read_json(archive, info):
    if info.file_size > MAX_JSON:
        raise ValueError('COCO JSON exceeds bounded metadata size')
    return json.loads(archive.read(info), parse_constant=lambda _: (_ for _ in ()).throw(
        ValueError('Nonfinite JSON constant')))


def inspect_station(path, station, should_cancel=lambda: False):
    """Only ZIP directory/COCO; original RGB payload remains compressed and unchanged.

    Verifies associations and numeric bounds, not visible corners, image decoding,
    annotation truth or downstream training eligibility.
    """
    _identity(path, station.size, station.sha256)
    with zipfile.ZipFile(path) as archive:
        members, seen, expanded = {}, set(), 0
        if len(archive.infolist()) > station.images + 10:
            raise ValueError('Unexpected ZIP entry count')
        for info in archive.infolist():
            _cancel(should_cancel)
            name = checked_member_name(info, seen)
            if stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Special ZIP entries are not public dataset payload')
            if info.is_dir():
                if name.rstrip('/') not in {station.split, station.prefix.rstrip('/'),
                                            station.prefix + 'images'}:
                    raise ValueError('Unexpected ZIP directory')
                continue
            if not name.startswith(station.prefix) or info.file_size < 1:
                raise ValueError('Unexpected ZIP member')
            relative = name[len(station.prefix):]
            validate_dataset_relative_path(relative)
            if relative != 'instances.json' and not (
                relative.startswith('images/') and relative.count('/') == 1
                and relative.lower().endswith('.jpg')):
                raise ValueError('Unexpected station payload')
            expanded += info.file_size
            members[relative] = info
        if len(members) != station.images + 1 or expanded != station.unpacked:
            raise ValueError('Publisher payload totals differ')
        data = _read_json(archive, members['instances.json'])
    if not isinstance(data, dict):
        raise ValueError('COCO object required')
    categories = data.get('categories')
    if (not isinstance(categories, list) or len(categories) != 1
            or not isinstance(categories[0], dict) or categories[0].get('name') != 'pv_panel'
            or type(categories[0].get('id')) is not int):
        raise ValueError('Expected single whole-module pv_panel category')
    images, annotations = data.get('images'), data.get('annotations')
    if (not isinstance(images, list) or len(images) != station.images
            or not isinstance(annotations, list) or len(annotations) != station.annotations):
        raise ValueError('Publisher annotation totals differ')
    indexed, referenced_files, counts = {}, set(), {}
    for image in images:
        _cancel(should_cancel)
        if (not isinstance(image, dict) or type(image.get('id')) is not int
                or image['id'] in indexed or not _positive_int(image.get('width'))
                or not _positive_int(image.get('height'))):
            raise ValueError('Invalid or duplicate COCO image')
        name = image.get('file_name')
        if not isinstance(name, str):
            raise ValueError('Image filename missing')
        validate_dataset_relative_path(name)
        # COCO commonly stores basename or images/basename, both within this station.
        name = name if name.startswith('images/') else 'images/' + name
        if name not in members or name in referenced_files:
            raise ValueError('Missing, duplicate or cross-station image reference')
        referenced_files.add(name)
        indexed[image['id']] = image
        counts[image['id']] = 0
    if referenced_files != set(members) - {'instances.json'}:
        raise ValueError('Unindexed JPEG')
    ids, fragments = set(), 0
    for annotation in annotations:
        _cancel(should_cancel)
        if (not isinstance(annotation, dict) or type(annotation.get('id')) is not int
                or annotation['id'] in ids or type(annotation.get('image_id')) is not int
                or annotation['image_id'] not in indexed
                or type(annotation.get('category_id')) is not int
                or annotation['category_id'] != categories[0]['id']
                or annotation.get('iscrowd', 0) != 0):
            raise ValueError('Invalid annotation association')
        image = indexed[annotation['image_id']]
        width, height = image['width'], image['height']
        box, polygons, area = annotation.get('bbox'), annotation.get('segmentation'), annotation.get('area')
        if (not isinstance(box, list) or len(box) != 4 or not all(map(_number, box))
                or min(box[:2]) < 0 or min(box[2:]) <= 0
                or box[0] + box[2] > width + 1 or box[1] + box[3] > height + 1
                or not _number(area) or not 0 < area <= width * height
                or not isinstance(polygons, list) or not polygons):
            raise ValueError('Invalid COCO module geometry')
        for polygon in polygons:
            if (not isinstance(polygon, list) or not 6 <= len(polygon) <= 10000
                    or len(polygon) % 2 or not all(map(_number, polygon))
                    or not all(0 <= x <= width and 0 <= y <= height
                               for x, y in zip(polygon[::2], polygon[1::2]))):
                raise ValueError('Invalid COCO polygon coordinates')
        fragments += int(len(polygons) > 1)
        ids.add(annotation['id'])
        counts[annotation['image_id']] += 1
    return dict(station=station.station, split=station.split, images=len(images),
        annotation_observations=len(annotations), images_without_annotations=sum(v == 0 for v in counts.values()),
        multi_fragment_instances=fragments, archive_bytes=station.size, archive_sha256=station.sha256)


def _report(root, should_cancel):
    for name, (size, checksum) in DOCUMENTS.items():
        _cancel(should_cancel)
        _identity(root / name, size, checksum)
    rows = [inspect_station(root / item.name, item, should_cancel) for item in STATIONS]
    rights = PublicDatasetRecord('pvis-10k-1.0.0', SOURCE, ImageModality.RGB, 'CC-BY-4.0')
    return dict(check=CHECK, status='inventory_verified_not_training_ready', source_url=SOURCE,
        version='1.0.0', stations=rows, images=sum(r['images'] for r in rows),
        annotation_observations=sum(r['annotation_observations'] for r in rows),
        publisher_sha256_verified=True, station_disjoint=True, validation_stations=0,
        documents={name: dict(bytes=size, sha256=checksum) for name, (size, checksum) in DOCUMENTS.items()},
        license_declared=rights.license_name, license_decision=rights.decision.value,
        commercial_training_approved=rights.can_train_commercially(ImageModality.RGB),
        annotation_policy='whole_module_projected_including_occluded_parts',
        visible_corner_eligibility_verified=False, physical_module_ids_confirmed=False,
        image_decoding_verified=False, training_authorized=False, training_started=False,
        customer_images_read=False, images_exported=False, model_updated=False,
        accuracy_verified=False, automatically_accepted=False, coverage_verified=False,
        georeferencing_verified=False, temperature_verified=False, pair_registered=False,
        production_approved=False,
        notice='Nur öffentliche RGB-Paket-/Annotationsprüfung. Beobachtungen sind keine eindeutigen Modul-IDs. '
               'Testanlage bleibt unangetastet für Modell-/Parameterwahl. Eigene Validierungsanlage fehlt; '
               'verdeckte Modulflächen vor Trainingsnutzung klären. Kein Modell oder Training gestartet.')


def intake(prefix, archive_dir=None, should_cancel=lambda: False, show=False):
    root = local(prefix)
    source = local(archive_dir) if archive_dir is not None else None
    marker = root / 'pvis-intake.json'
    if root.exists() and any(root.iterdir()):
        if not marker.is_file() or json.loads(local(marker).read_text('utf-8')) != {'check': CHECK}:
            raise ValueError('Use a separate empty PVIS reference folder')
    if show and not root.is_dir():
        raise FileNotFoundError
    root.mkdir(parents=True, exist_ok=True)
    with package_lock(root, 'pvis-package.lock'):
        if not marker.exists():
            if show:
                raise FileNotFoundError
            atomic_json(marker, {'check': CHECK})
        target = local(root / 'reference.json')
        if show:
            saved = json.loads(target.read_text('utf-8'))
            actual = _report(root, should_cancel)
            if saved != actual:
                raise ValueError('Reference report or public packages changed')
            return actual
        _cancel(should_cancel)
        missing = sum(size for name, (size, _) in DOCUMENTS.items() if not (root/name).exists())
        missing += sum(item.size for item in STATIONS if not (root/item.name).exists())
        if shutil.disk_usage(root).free < missing + 50_000_000:
            raise OSError(28, 'Insufficient public-reference storage')
        for name, (size, checksum) in DOCUMENTS.items():
            _receive(root/name, size, checksum, source, should_cancel)
        for item in STATIONS:
            print(f'Pruefe oeffentliche Anlage {item.station} ({item.split}) ...', file=sys.stderr, flush=True)
            _receive(root/item.name, item.size, item.sha256, source, should_cancel)
        actual = _report(root, should_cancel)
        _cancel(should_cancel)
        atomic_json(target, actual)
        return actual


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default=r'E:\SolarCheck-PVIS-Referenz')
    parser.add_argument('--archive-dir', help='Bewusst lokal geladene zwei ZIPs plus drei Quellen-Dokumente')
    parser.add_argument('--show', action='store_true', help='Gespeicherte Referenz nur lokal nachpruefen')
    args = parser.parse_args(argv)
    if args.show and args.archive_dir:
        parser.error('--show benoetigt keinen Quellordner')
    try:
        result = intake(args.prefix, args.archive_dir, show=args.show)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        return 0
    except KeyboardInterrupt:
        code, status = 'CANCELLED', 'cancelled'
    except Exception as error:
        cause = getattr(error, 'reason', error)
        code = ('TLS_CERTIFICATE' if isinstance(cause, ssl.SSLCertVerificationError)
                else 'NETWORK_ERROR' if isinstance(error, urllib.error.URLError)
                else 'PUBLIC_REFERENCE_MISSING' if isinstance(error, FileNotFoundError)
                else 'PACKAGE_OR_REPORT_INVALID' if isinstance(error, (ValueError, zipfile.BadZipFile))
                else 'OUTPUT_FULL' if isinstance(error, OSError) and (
                    error.errno == 28 or getattr(error, 'winerror', None) == 112)
                else 'LOCAL_IO' if isinstance(error, OSError) else 'INTAKE_FAILED')
        status = 'failed'
    print(json.dumps(dict(check='solarcheck-pvis-reference-failure-1', status=status,
        error_code=code, training_started=False, customer_images_read=False, production_approved=False,
        next_step='Nur Diagnoseblock mitteilen. Bei TLS: Zertifikatsprüfung eingeschaltet lassen; '
                  'offizielle Dateien im Browser laden und --archive-dir nutzen. '
                  'Neustart verwendet vollständige geprüfte Dateien; --show lädt nichts herunter.')))
    return 130 if code == 'CANCELLED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
