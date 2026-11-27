"""Bounded, publisher-pinned public training supplements; no customer sources.

The caller supplies an in-memory ZIP. No network/installation or archive
extraction happens here. The older, source-bound intake stays unchanged.
"""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import math
import re
from pathlib import PurePosixPath
import stat
import zipfile
import numpy as np

from pathlib import Path

from .pv_synthetic_training import _local
from . import pvis_learning_corpus as numeric


@dataclass(frozen=True)
class PublicSite:
    station: str
    images: int
    annotations: int
    unpacked: int
    size: int
    sha256: str

    @property
    def name(self):
        return f'PVDataset_train_{self.station}.zip'

    @property
    def prefix(self):
        return f'train/{self.station}/'


SITES = {
    '018': PublicSite('018', 224, 34709, 595099834, 576581875,
        '37c395176357083b5a9f0eb56eac0433950b25ed2dd42a51d004e6ad9642472d'),
    '029': PublicSite('029', 289, 41691, 853120872, 830881450,
        '99170f7e233563bd032146615cc89e3f2898a63eb4eb3ec9444388ab2f2fc95b'),
}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def verified_zip(buffer, station):
    """Verify the entire byte identity before reading any public image payload."""
    if station not in SITES or type(buffer) is not BytesIO:
        raise PermissionError('Only the declared public training supplements')
    spec = SITES[station]
    view = buffer.getbuffer()
    if len(view) != spec.size or sha256(view).hexdigest() != spec.sha256:
        raise ValueError('Publisher public training archive checksum differs')
    del view
    buffer.seek(0)
    archive = zipfile.ZipFile(buffer)
    try:
        entries, total, names = {}, 0, set()
        if len(archive.infolist()) > spec.images+10:
            raise ValueError('Unexpected public archive member count')
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if (name in names or '\\' in name or path.is_absolute() or '..' in path.parts
                    or info.flag_bits & 1
                    or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFDIR, stat.S_IFREG)):
                raise ValueError('Unexpected public archive member')
            names.add(name)
            if info.is_dir():
                if name.rstrip('/') not in ('train', spec.prefix.rstrip('/'), spec.prefix+'images'):
                    raise ValueError('Unexpected public archive directory')
                continue
            if not name.startswith(spec.prefix):
                raise ValueError('Cross-station public archive member')
            relative = name[len(spec.prefix):]
            if (relative != 'instances.json' and not (relative.startswith('images/')
                    and relative.count('/') == 1 and relative.lower().endswith('.jpg'))):
                raise ValueError('Unexpected public training payload')
            if info.file_size <= 0:
                raise ValueError('Empty public payload')
            total += info.file_size
            entries[relative] = info
        if len(entries) != spec.images+1 or total != spec.unpacked:
            raise ValueError('Publisher public payload totals differ')
        info = entries['instances.json']
        if info.file_size > 64_000_000:
            raise ValueError('Bounded public COCO metadata required')
        coco = json.loads(archive.read(info), parse_constant=lambda _: (_ for _ in ()).throw(
            ValueError('Nonfinite public metadata')))
        _validate_coco(coco, spec, entries)
        archive._solarcheck_verified_public_source = (station, spec.size, spec.sha256)
        return archive, coco
    except BaseException:
        archive.close()
        raise


def _validate_coco(coco, spec, entries):
    if not isinstance(coco, dict):
        raise ValueError('Public COCO object required')
    categories = coco.get('categories')
    if (not isinstance(categories, list) or len(categories) != 1
            or not isinstance(categories[0], dict)
            or categories[0].get('name') != 'pv_panel' or type(categories[0].get('id')) is not int):
        raise ValueError('Published whole-module class required')
    images, annotations = coco.get('images'), coco.get('annotations')
    if (not isinstance(images, list) or len(images) != spec.images
            or not isinstance(annotations, list) or len(annotations) != spec.annotations):
        raise ValueError('Publisher COCO totals differ')
    indexed, files, ids = {}, set(), set()
    for image in images:
        if (not isinstance(image, dict) or type(image.get('id')) is not int or image['id'] in indexed
                or any(type(image.get(k)) is not int or image[k] <= 0 for k in ('width', 'height'))):
            raise ValueError('Invalid public image metadata')
        name = image.get('file_name')
        if not isinstance(name, str):
            raise ValueError('Public image filename missing')
        relative = name if name.startswith('images/') else 'images/'+name
        if relative not in entries or relative in files:
            raise ValueError('Cross-station or duplicate public image')
        files.add(relative)
        indexed[image['id']] = image
    if files != set(entries)-{'instances.json'}:
        raise ValueError('Unindexed public image')
    for annotation in annotations:
        if (not isinstance(annotation, dict) or type(annotation.get('id')) is not int or annotation['id'] in ids
                or type(annotation.get('image_id')) is not int
                or type(annotation.get('category_id')) is not int
                or annotation.get('image_id') not in indexed
                or annotation.get('category_id') != categories[0]['id']
                or annotation.get('iscrowd', 0) != 0):
            raise ValueError('Invalid public annotation association')
        ids.add(annotation['id'])
        image = indexed[annotation['image_id']]
        box, polygons, area = annotation.get('bbox'), annotation.get('segmentation'), annotation.get('area')
        if (not isinstance(box, list) or len(box) != 4 or not all(map(_number, box))
                or min(box[:2]) < 0 or min(box[2:]) <= 0
                or box[0]+box[2] > image['width']+1 or box[1]+box[3] > image['height']+1
                or not _number(area) or not 0 < area <= image['width']*image['height']
                or not isinstance(polygons, list) or not polygons):
            raise ValueError('Invalid public module geometry')
        for polygon in polygons:
            if (not isinstance(polygon, list) or not 6 <= len(polygon) <= 10000
                    or len(polygon) % 2 or not all(map(_number, polygon))
                    or not all(0 <= x <= image['width'] and 0 <= y <= image['height']
                               for x, y in zip(polygon[::2], polygon[1::2]))):
                raise ValueError('Invalid public polygon')


def _geometry_identity():
    from . import pvis_public_context as context
    from . import pvis_image_adapter as original
    from . import pvis_public_training_data as reduction
    return {key: sha256(Path(module.__file__).read_bytes()).hexdigest()
            for key, module in dict(context=context, original=original, reduction=reduction).items()}


def _seal(value):
    value = dict(value)
    value.pop('manifest_sha256', None)
    value['manifest_sha256'] = sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return value


def read_context_cache(root, station):
    """Check a selected numeric subset; never redownload an already verified site."""
    if station not in SITES:
        raise PermissionError('Declared public training supplement required')
    folder = _local(Path(root)/station)
    manifest = _local(folder/'contexts.json')
    if not manifest.exists():
        return None
    if manifest.stat().st_size > 1_000_000:
        raise ValueError('Public subset manifest too large')
    value = json.loads(manifest.read_text(encoding='utf-8'))
    return _read_cache_value(folder, value, station)


def _read_cache_value(folder, value, station):
    spec = SITES[station]
    if (not isinstance(value, dict) or value != _seal(value)
            or value.get('check') != 'solarcheck-pvis-public-context-cache-1'
            or value.get('profile') != 'native512-area256-four-contexts-1'
            or value.get('station') != station or value.get('split') != 'train'
            or value.get('source_archive_sha256') != spec.sha256
            or value.get('source_archive_bytes') != spec.size
            or value.get('publisher_archive_sha256_verified_at_intake') is not True
            or value.get('geometry_source_sha256') != _geometry_identity()
            or value.get('source_url') != 'https://zenodo.org/records/23886365'
            or value.get('customer_images') != 0 or value.get('test_images') != 0
            or value.get('license_declared') != 'CC-BY-4.0'
            or value.get('license_decision') != 'unreviewed'
            or value.get('commercial_training_approved') is not False):
        raise ValueError('Public subset identity or scope changed')
    rows = value.get('samples')
    if not isinstance(rows, list) or not 20 <= len(rows) <= 80:
        raise ValueError('Bounded20-image public subset required')
    seen, image_ids, results = set(), set(), []
    for row in rows:
        if (not isinstance(row, dict) or row.get('station') != station or row.get('split') != 'train'
                or type(row.get('image_id')) is not int
                or type(row.get('instances')) is not int or not 1 <= row['instances'] <= 128
                or not all(isinstance(row.get(k), str) and re.fullmatch('[0-9a-f]{64}', row[k])
                           for k in ('sample_id', 'data_sha256'))
                or row['sample_id'] in seen):
            raise ValueError('Public context row changed')
        record = row.get('record')
        if (not isinstance(record, dict) or record.get('station') != station
                or record.get('split') != 'train' or record.get('image_id') != row['image_id']
                or record.get('retained_instances') != row['instances']):
            raise ValueError('Public context provenance differs')
        seen.add(row['sample_id'])
        image_ids.add(row['image_id'])
        rgb, targets = numeric.read_crop(folder, row)
        results.append((rgb, targets, row['record']))
    if len(image_ids) != 20:
        raise ValueError('Public source image count changed')
    return results


def write_context_cache(root, station, samples, *, verified_archive):
    """Publish only after full publisher-SHA verification and selected decoding.

    The caller must obtain these samples from verified_zip(). Cache public
    numeric crops, not the large source ZIP; interrupted transfers stay unpublished.
    """
    if station not in SITES:
        raise PermissionError('Declared public training supplement required')
    spec = SITES[station]
    if (not isinstance(verified_archive, zipfile.ZipFile)
            or getattr(verified_archive, '_solarcheck_verified_public_source', None)
               != (station, spec.size, spec.sha256)):
        raise ValueError('A completely verified public source is required before publication')
    folder = _local(Path(root)/station)
    folder.mkdir(parents=True, exist_ok=True)
    if (folder/'contexts.json').exists():
        raise ValueError('Preserve the already published public subset')
    rows = []
    for rgb, targets, record in samples:
        if record.get('station') != station or record.get('split') != 'train':
            raise ValueError('Training role or public site differs')
        name = sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        row = dict(station=station, split='train', image_id=record['image_id'],
            sample_id=name, record=record, instances=len(np.unique(targets[targets > 0])),
            data_sha256=numeric.write_crop(folder, name, rgb, targets))
        numeric.read_crop(folder, row)
        rows.append(row)
    value = _seal(dict(check='solarcheck-pvis-public-context-cache-1',
        profile='native512-area256-four-contexts-1', station=station, split='train',
        source_url='https://zenodo.org/records/23886365', source_archive_sha256=spec.sha256,
        source_archive_bytes=spec.size, publisher_archive_sha256_verified_at_intake=True,
        geometry_source_sha256=_geometry_identity(), license_declared='CC-BY-4.0',
        license_decision='unreviewed', commercial_training_approved=False,
        customer_images=0, test_images=0, samples=rows))
    _read_cache_value(folder, value, station)
    target = _local(folder/'contexts.json')
    temporary = _local(folder/'contexts.next.json')
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2), encoding='utf-8')
    temporary.replace(target)
    read_context_cache(root, station)
