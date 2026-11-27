"""Larger public-only corpus using the unchanged audited native512 ->256 adapter."""
from hashlib import sha256
from pathlib import Path
import json
import re
import tempfile
import zipfile

import numpy as np

from .pvis_public_training_data import fingerprint, encoded, training_arrays, SOURCE, PROFILE
from .pv_synthetic_training import _local
from .pvis_instance_training import _digest, _json_atomic

CHECK = 'solarcheck-pvis-learning-corpus-1'
TRAIN = 58
VALIDATION = 24
SEED = 6400
POLICY = 'all_eligible_train009_first24_seeded_validation033_including_previous8'


def seal(value):
    value = dict(value)
    for key in ('manifest_sha256', 'dataset_id', 'snapshot_id'): value.pop(key, None)
    value['snapshot_id'] = fingerprint(dict(config=value['config'], samples=value['samples']))
    value['dataset_id'] = fingerprint(dict(snapshot_id=value['snapshot_id'], input_profile=PROFILE))
    value['manifest_sha256'] = fingerprint(value)
    return value


def validate(value, *, synthetic=False):
    if (not isinstance(value, dict) or value != seal(value) or value.get('check') != CHECK
            or value.get('synthetic_only') is not synthetic or value.get('source_url') != SOURCE
            or value.get('profile') != PROFILE or value.get('label_policy') != 'pvis-projected-whole-module-1'
            or value.get('license_declared') != 'CC-BY-4.0' or value.get('license_decision') != 'unreviewed'
            or value.get('commercial_training_approved') is not False or value.get('test_images') != 0
            or value.get('customer_images') != 0 or value.get('corpus_id') != fingerprint(value['config'])
            or value.get('size') not in ((64, 256) if synthetic else (256,))):
        raise ValueError('Qualified public corpus identity required')
    rows = value.get('samples'); counts = dict(train=0, validation=0); seen = set()
    if not isinstance(rows, list) or not 2 <= len(rows) <= TRAIN+VALIDATION:
        raise ValueError('Bounded train/validation corpus required')
    for row in rows:
        if ((row.get('station'), row.get('split')) not in {('009', 'train'), ('033', 'validation')}
                or row.get('corpus_id') != value['corpus_id']
                or not isinstance(row.get('sample_id'), str) or not re.fullmatch('[0-9a-f]{64}', row['sample_id'])
                or row['sample_id'] in seen or type(row.get('instances')) is not int or not 1 <= row['instances'] <= 128
                or not all(isinstance(row.get(k), str) and re.fullmatch('[0-9a-f]{64}', row[k])
                           for k in ('data_sha256', 'source_record_sha256'))):
            raise ValueError('Changed source, duplicate crop or station leakage')
        seen.add(row['sample_id']); counts[row['split']] += 1
    if (not all(counts.values()) or value.get('split_counts') != counts
            or not synthetic and counts != dict(train=TRAIN, validation=VALIDATION)):
        raise ValueError('Public corpus partition differs')
    return value


def write_crop(folder, name, rgb, instances):
    """Only primitive arrays. Publication follows a complete, closed ZIP write."""
    path = _local(folder/(name+'.npz')); temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, suffix='.next', delete=False) as stream:
            temporary = Path(stream.name); np.savez_compressed(stream, rgb=rgb, instances=instances)
        temporary.replace(path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return _digest(path)


def read_crop(folder, row, *, size=256):
    path = _local(folder/(row['sample_id']+'.npz'))
    if path.stat().st_size > 1_000_000 or _digest(path) != row['data_sha256']:
        raise ValueError('Saved public crop changed')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if (sorted(i.filename for i in entries) != ['instances.npy', 'rgb.npy']
                or sum(i.file_size for i in entries) > 500_000):
            raise ValueError('Unexpected primitive crop members')
    with np.load(path, allow_pickle=False) as arrays:
        rgb, target = arrays['rgb'].copy(), arrays['instances'].copy()
    if (rgb.shape != (size, size, 3) or rgb.dtype != np.uint8 or target.shape != (size, size)
            or target.dtype != np.int32 or target.min() < -1 or target.max() > 10000
            or len(np.unique(target[target > 0])) != row['instances'] or not np.any(target == 0)):
        raise ValueError('Public RGB/instance crop differs')
    return rgb, target


def read_corpus(folder, manifest, *, synthetic=False):
    validate(manifest, synthetic=synthetic)
    if folder.name != manifest['corpus_id']: raise ValueError('Corpus folder identity differs')
    arrays = [read_crop(folder, row, size=manifest['size']) for row in manifest['samples']]
    return np.stack([a[0] for a in arrays]), np.stack([a[1] for a in arrays])


def prepare(source, output, audit, *, should_cancel=lambda: False, synthetic=False):
    """Caller holds its learning-root lock. Source audit obtains its own lock first."""
    source, output = _local(source), _local(output)
    state = audit.audit(source, show=True, should_cancel=should_cancel)
    with audit.package_lock(source, 'pvis-package.lock'):
        if audit._json(source/audit.REPORT) != state: raise ValueError('Source audit changed')
        return _prepare(source, output, audit, state, should_cancel, synthetic)


def _prepare(source, output, audit, state, should_cancel, synthetic):
    config = dict(adapter_id=state['adapter_id'], audit_manifest_sha256=state['manifest_sha256'],
        partition_sha256=state['partition_sha256'], policy=POLICY, seed=SEED,
        source_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    folder = _local(output/fingerprint(config)); folder.mkdir(parents=True, exist_ok=True)
    if (folder/'corpus.json').exists():
        manifest = validate(audit._json(folder/'corpus.json'), synthetic=synthetic)
        read_corpus(folder, manifest, synthetic=synthetic)
        return folder, manifest
    journal = _local(source/audit.FOLDER/state['adapter_id'])
    completed = audit._json(journal/'completed.json'); selections = dict(train=[], validation=[])
    for name, expected_sha in completed['records'].items():
        if _digest(journal/name) != expected_sha: raise ValueError('Audited public image record changed')
        record = audit._json(journal/name)
        if record['eligible']:
            rank = sha256(f'{SEED}:{record["station"]}:{record["image_id"]}'.encode()).hexdigest()
            selections[record['split']].append((rank, record))
    for role in selections: selections[role].sort(key=lambda r: r[0])
    selections['validation'] = selections['validation'][:VALIDATION]
    if not synthetic and (len(selections['train']) != TRAIN or len(selections['validation']) != VALIDATION):
        raise ValueError('All58 qualified training crops and24 validation crops required')
    selected = {(r['station'], r['image_id']): r for values in selections.values() for _, r in values}
    rows = {}
    from . import pvis_image_adapter as pixels
    for spec, role, archive, image, annotations in audit._sources(source):
        if should_cancel(): raise KeyboardInterrupt
        key = (spec.station, image['id'])
        if key not in selected: continue
        expected = selected[key]; name = fingerprint(dict(station=spec.station, image_id=image['id']))
        record_path = _local(folder/(name+'.json'))
        if record_path.exists():
            row = audit._json(record_path)
            if (row.get('corpus_id') != folder.name or row.get('source_record_sha256') != expected['record_sha256'] or row.get('sample_id') != name
                    or row.get('station') != spec.station or row.get('split') != role):
                raise ValueError('Saved crop belongs to another source')
            read_crop(folder, row)
        else:
            filename = image['file_name']; filename = filename if filename.startswith('images/') else 'images/'+filename
            entry = archive.getinfo(spec.prefix+filename)
            if entry.file_size > pixels.MAX_JPEG: raise ValueError('Public JPEG too large')
            sample = pixels.load_sample(archive.read(entry), image, annotations, station=spec.station, split=role)
            if sample.record != expected: raise ValueError('Public crop differs from audited runtime')
            rgb, target = training_arrays(sample.rgb, sample.instances)
            row = dict(corpus_id=folder.name, sample_id=name, station=spec.station, split=role,
                source_record_sha256=expected['record_sha256'], instances=len(np.unique(target[target > 0])),
                data_sha256=write_crop(folder, name, rgb, target))
            if should_cancel(): raise KeyboardInterrupt
            _json_atomic(record_path, row)
        rows[key] = row
        print(f'Oeffentlicher Lernkorpus: {len(rows)}/{len(selected)} Ausschnitte gespeichert', flush=True)
    ordered = [rows[(r['station'], r['image_id'])] for role in ('train', 'validation') for _, r in selections[role]]
    manifest = seal(dict(check=CHECK, corpus_id=fingerprint(config), config=config, samples=ordered,
        size=256,
        split_counts={role: len(values) for role, values in selections.items()}, synthetic_only=synthetic,
        source_url=SOURCE, profile=PROFILE, label_policy='pvis-projected-whole-module-1',
        license_declared='CC-BY-4.0', license_decision='unreviewed', commercial_training_approved=False,
        test_images=0, customer_images=0))
    read_corpus(folder, manifest, synthetic=synthetic)
    if should_cancel(): raise KeyboardInterrupt
    _json_atomic(folder/'corpus.json', manifest)
    return folder, manifest
