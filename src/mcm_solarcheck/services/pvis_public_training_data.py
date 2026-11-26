"""Numeric public-only research package; no Torch, pickle, private dataset or trainer."""
from hashlib import sha256
import json
import re
import zipfile

import numpy as np

CHECK = 'solarcheck-pvis-public-training-data-1'
PROFILE = 'pvis-rgb-area256-instance-nearest-allvalid-1'
SIZE = 256
SAMPLES = 8
SEED = 6400
MAX_BYTES = 30_000_000
SOURCE = 'https://zenodo.org/records/23886365'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return sha256(encoded(value).encode('utf-8')).hexdigest()


def seal_manifest(value):
    value = dict(value)
    value['snapshot_id'] = fingerprint(dict(config=value['config'], samples=value['samples']))
    value['dataset_id'] = fingerprint(dict(snapshot_id=value['snapshot_id'],
        profile=value['profile'], data_sha256=value['data_sha256'], size=value['size']))
    value['manifest_sha256'] = fingerprint(value)
    return value


def training_arrays(rgb, instances):
    """2x area RGB, exact nearest instance ID, conservative all-contributors validity."""
    if rgb.shape != (512, 512, 3) or rgb.dtype != np.uint8 or instances.shape != (512, 512) or instances.dtype != np.int32:
        raise ValueError('Verified native512 RGB and int32 instances required')
    # Integer 2x area mean with half-up rounding; no OpenCV/runtime resampling.
    pixels = ((rgb.reshape(SIZE, 2, SIZE, 2, 3).astype(np.uint16).sum(axis=(1, 3))+2)//4).astype(np.uint8)
    labels = instances[1::2, 1::2].copy()  # nearest source pixel center
    valid = (instances >= 0).reshape(SIZE, 2, SIZE, 2).all(axis=(1, 3))
    labels[~valid] = -1
    if not np.any(labels > 0) or not np.any(labels == 0):
        raise ValueError('Foreground/background lost under conservative reduction')
    return pixels, labels


def validate_manifest(value, *, allow_synthetic=False):
    if not isinstance(value, dict): raise ValueError('Public package manifest required')
    body = dict(value); check = body.pop('manifest_sha256', None)
    if (check != fingerprint(body) or value.get('check') != CHECK
            or value.get('scope') != 'explicit_public_pvis_research_only'
            or value.get('profile') != PROFILE or value.get('license_declared') != 'CC-BY-4.0'
            or value.get('license_decision') != 'unreviewed'
            or value.get('commercial_training_approved') is not False
            or value.get('source_url') != SOURCE or value.get('dataset_version') != '1.0.0'
            or value.get('label_policy') != 'pvis-projected-whole-module-1'
            or value.get('test_images') != 0 or value.get('customer_images') != 0):
        raise ValueError('Public package identity or scope differs')
    synthetic = value.get('synthetic_only') is True
    if type(value.get('synthetic_only')) is not bool:
        raise ValueError('Explicit public or synthetic identity required')
    if synthetic and not allow_synthetic: raise ValueError('Synthetic fixture is not a public pilot package')
    if (not isinstance(value.get('config'), dict)
            or value.get('preparation_id') != fingerprint(value['config'])
            or value.get('size') != (64 if synthetic else SIZE)):
        raise ValueError('Preparation identity or numeric resolution changed')
    rows = value.get('samples')
    if not isinstance(rows, list) or not rows or len(rows) > 2*SAMPLES:
        raise ValueError('Bounded public train/validation samples required')
    counts, seen = dict(train=0, validation=0), set()
    for row in rows:
        if (not isinstance(row, dict) or (row.get('station'), row.get('split')) not in
                {('009', 'train'), ('033', 'validation')} or not isinstance(row.get('sample_id'), str)
                or not 1 <= len(row['sample_id']) <= 100 or row['sample_id'] in seen
                or not isinstance(row.get('source_record_sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', row['source_record_sha256'])):
            raise ValueError('Changed station role, duplicate sample or test leakage')
        seen.add(row['sample_id']); counts[row['split']] += 1
    expected = value.get('split_counts')
    if counts != expected or not all(counts.values()) or (not synthetic and counts != dict(train=SAMPLES, validation=SAMPLES)):
        raise ValueError('Public split counts differ')
    for key in ('dataset_id', 'snapshot_id', 'data_sha256'):
        if not isinstance(value.get(key), str) or not re.fullmatch('[0-9a-f]{64}', value[key]):
            raise ValueError('Bound numeric data and lineage required')
    resealed = dict(value)
    for key in ('manifest_sha256', 'dataset_id', 'snapshot_id'): resealed.pop(key)
    if seal_manifest(resealed) != value: raise ValueError('Dataset lineage differs')
    return value


def read_arrays(path, manifest, *, allow_synthetic=False):
    validate_manifest(manifest, allow_synthetic=allow_synthetic)
    if path.stat().st_size > MAX_BYTES or sha256(path.read_bytes()).hexdigest() != manifest['data_sha256']:
        raise ValueError('Numeric training package changed')
    with zipfile.ZipFile(path) as zipped:
        if (sorted(i.filename for i in zipped.infolist()) != ['instances.npy', 'rgb.npy']
                or sum(i.file_size for i in zipped.infolist()) > MAX_BYTES):
            raise ValueError('Unexpected numeric members or size')
    with np.load(path, allow_pickle=False) as data:
        rgb, labels = data['rgb'].copy(), data['instances'].copy()
    size = manifest.get('size')
    expected_size = 64 if allow_synthetic and manifest.get('synthetic_only') else SIZE
    if (size != expected_size or rgb.dtype != np.uint8 or labels.dtype != np.int32
            or rgb.shape != (len(manifest['samples']), size, size, 3)
            or labels.shape != (len(manifest['samples']), size, size)
            or labels.min() < -1 or labels.max() > 10000):
        raise ValueError('Wrong numeric array shape, type or labels')
    for mask in labels:
        if not np.any(mask > 0) or not np.any(mask == 0) or len(np.unique(mask[mask > 0])) > 128:
            raise ValueError('Invalid bounded instance training target')
    return rgb, labels
