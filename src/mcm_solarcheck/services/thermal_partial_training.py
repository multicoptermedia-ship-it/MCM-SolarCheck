"""Local annotation preparation only: no image export, trainer or model changes.

Reuses reviewed geometry, snapshot and spatial split contracts. The separate
record never grants data rights or makes partial Thermal a registered pair.
"""
from dataclasses import asdict
from hashlib import sha256
import json
import unicodedata
from uuid import uuid4

import cv2
import numpy as np
import rasterio
from rasterio.windows import Window

from .thermal_partial_comparison import FLAGS, _local, verify_partial_comparison
from .thermal_partial_pv import load_module_review, active_entries
from .orthophoto_pv_modules import _cancel, _rgb_valid_pixels, _polygon_mask
from ..review.training_geometry import ReviewedGeometry, validate_geometry_bounds
from ..review.training_snapshot import TrainingSnapshot
from ..review.training_export import build_spatial_training_index
from ..vision.polygon_geometry import convex_polygon_iou

STATE = 'pv-learning-preparation.LOCAL.json'
CHECK = 'solarcheck-pv-learning-preparation-1'
FALSE_FLAGS = (*FLAGS, 'accuracy_verified', 'physical_module_ids_confirmed',
    'automatically_accepted', 'training_authorized', 'training_started',
    'images_exported', 'model_updated')
SPLIT_LABELS = dict(train='Training', validation='Validierung', test='Unabhängige Prüfung')


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _digest(value):
    return sha256(_json(value).encode('utf-8')).hexdigest()


def _text(value):
    if (not isinstance(value, str) or not 1 <= len(value.strip()) <= 100
            or any(ord(c) < 32 for c in value)):
        raise ValueError('Prüfname und Anlagengruppe benötigen jeweils 1 bis 100 Zeichen.')
    return value.strip()


def normalize_group(value):
    return _text(' '.join(unicodedata.normalize('NFKC', _text(value)).casefold().split()))


def _saved_region(comparison, key):
    regions, _ = load_module_review(comparison)
    if key not in regions:
        raise ValueError('Zuerst den aktuellen Modulausschnitt lokal speichern.')
    return regions[key]


def _read(comparison):
    path = comparison.folder / STATE
    if not path.exists() and not path.is_symlink():
        return None, None
    path = _local(path)
    if path.stat().st_size > 4_000_000:
        raise ValueError('Lokale Lernvorbereitung ist zu groß.')
    raw = path.read_bytes()
    data = json.loads(raw)
    if (not isinstance(data, dict) or data.get('check') != CHECK
            or data.get('fingerprints') != comparison.fingerprints
            or data.get('label') != comparison.label
            or any(data.get(k) is not False for k in FALSE_FLAGS)
            or not isinstance(data.get('regions'), dict) or len(data['regions']) > 20
            or normalize_group(data.get('group_id')) != data['group_id']):
        raise ValueError('Ungültige lokale Lernvorbereitung.')
    for key, entry in data['regions'].items():
        if (not isinstance(entry, dict) or set(entry) != {'review_sha256', 'reviewer', 'snapshot_id', 'manifest'}
                or not isinstance(entry['manifest'], dict)
                or entry['snapshot_id'] != _digest(entry['manifest'])
                or not isinstance(entry['review_sha256'], str) or len(entry['review_sha256']) != 64
                or entry['reviewer'] != _text(entry['reviewer'])
                or entry['manifest'].get('complete_annotation') is not True
                or entry['manifest'].get('region_key') != key
                or entry['manifest'].get('group_id') != data['group_id']
                or any(entry['manifest'].get(k) is not False for k in FALSE_FLAGS)):
            raise ValueError('Ungültiger gespeicherter Lernmusterstand.')
    return data, raw


def annotation_problem(region):
    entries = active_entries(region)
    if any(e['status'] == 'pending' for e in entries):
        return 'Zuerst alle offenen Umrisse beurteilen und Modul-Entwürfe lokal speichern.'
    if not any(e['status'] == 'outline_ok' for e in entries):
        return 'Mindestens einen ganzen Modulumriss passend beurteilen und lokal speichern.'
    return ''


def _overlapping(a, b):
    # IoU alone misses tiny false outlines inside a whole module. Measure
    # intersection relative to the SMALLER polygon, using the existing IoU.
    iou = convex_polygon_iou(a, b)
    if iou <= 0:
        return False
    areas = [abs(cv2.contourArea(np.asarray(p, dtype=np.float32))) for p in (a, b)]
    intersection = iou * sum(areas) / (1 + iou)
    return intersection > .05 * min(areas)


def _entry(comparison, key, region, reviewer, group):
    problem = annotation_problem(region)
    if problem:
        raise ValueError(problem)
    col, row, width, height = region['window']
    frame = 'RGB-' + comparison.fingerprints['rgb'] + ':' + key
    labels, geometries, polygons = [], [], []
    for entry in active_entries(region):
        if entry['status'] != 'outline_ok':
            continue  # Rejections/deletions are NOT background annotations.
        polygon = tuple((float(x-col), float(y-row)) for x, y in entry['proposal']['rgb_polygon_px'])
        if any(x <= 0 or y <= 0 or x >= width-1 or y >= height-1 for x, y in polygon):
            raise ValueError('Randmodule nicht als ganze Module übernehmen; einen geeigneten Ausschnitt wählen.')
        xs, ys = zip(*polygon)
        box = (min(xs), min(ys), max(xs), max(ys))
        if any(box[0] < bounds[2] and bounds[0] < box[2]
                and box[1] < bounds[3] and bounds[1] < box[3]
                and _overlapping(polygon, old) for old, bounds in polygons):
            raise ValueError('Überlappende passende Umrisse zuerst korrigieren oder verwerfen.')
        polygons.append((polygon, box))
        geometry = validate_geometry_bounds(ReviewedGeometry(frame, reviewer, 'rendered_rgb',
            box, polygon), width, height)
        label_id = _digest(dict(frame=frame, draft=entry['module_id']))
        labels.append(dict(label_id=label_id, source_frame_id=frame, module_id=None, finding_id=None,
            inspection_group_id='pv-site:' + group, defect_class='pv_module',
            draft_module_id=entry['module_id']))
        geometries.append(dict(label_id=label_id, **asdict(geometry)))
    manifest = dict(project_id='local-pv-annotation-preparation', region_key=key, group_id=group,
        complete_annotation=True, samples=[dict(sample_id=frame, source_frame_id=frame,
            source_file=str(comparison.rgb_path), modality='rgb', content_sha256=comparison.fingerprints['rgb'],
            source_window=region['window'])], labels=labels, geometries=geometries,
        **dict.fromkeys(FALSE_FLAGS, False))
    encoded = _json(manifest)
    snapshot = TrainingSnapshot(sha256(encoded.encode('utf-8')).hexdigest(), 1, len(labels), encoded)
    # All samples of the same plant/flight group receive the same deterministic
    # split, even across orthophotos. ROI-local IDs never act as leakage groups.
    index = build_spatial_training_index(snapshot, 'segmentation')
    assert len({r['split'] for r in index}) == 1
    return dict(review_sha256=_digest(region), reviewer=reviewer,
        snapshot_id=snapshot.snapshot_id, manifest=manifest)


def read_learning_preparation(comparison, key):
    """Reopen metadata without detection, export, model imports or training."""
    region = _saved_region(comparison, key)
    data, _ = _read(comparison)
    entry = data['regions'].get(key) if data else None
    current = bool(entry and entry['review_sha256'] == _digest(region))
    if current and _json(_entry(comparison, key, region, entry['reviewer'], data['group_id'])) != _json(entry):
        raise ValueError('Lernmuster passen nicht zu den gespeicherten Modulkorrekturen.')
    return dict(group_id=data['group_id'] if data else '', entry=entry, current=current, review_sha256=_digest(region),
        problem=annotation_problem(region), module_count=sum(e['status'] == 'outline_ok' for e in active_entries(region)))


def learning_index(entry):
    """Metadata index: polygons address the explicit source window, not full TIFF.

    This does not export raster crops or authorize a trainer to consume them.
    """
    manifest = entry['manifest']
    snapshot = TrainingSnapshot(entry['snapshot_id'], 1, len(manifest['labels']), _json(manifest))
    return tuple(dict(row, source_window=manifest['samples'][0]['source_window'],
        geometry_coordinate_frame='source_window') for row in build_spatial_training_index(snapshot, 'segmentation'))


def prepared_split(entry):
    return learning_index(entry)[0]['split']


def save_learning_preparation(comparison, key, *, reviewer, group_id, complete_annotation,
        expected_review_sha256, should_cancel=None):
    """Explicit atomic metadata save; preserves previous preparation on abort."""
    _cancel(should_cancel)
    if complete_annotation is not True:
        raise ValueError('Vollständige Beschriftung ausdrücklich bestätigen.')
    reviewer, group = _text(reviewer), normalize_group(group_id)
    region = _saved_region(comparison, key)
    if _digest(region) != expected_review_sha256:
        raise ValueError('Modulprüfung wurde geändert; Lernvorbereitung erneut öffnen und prüfen.')
    data, previous = _read(comparison)
    if data and data['group_id'] != group:
        raise ValueError('Alle Ausschnitte dieses Orthofotos müssen dieselbe Anlagengruppe behalten.')
    entry = _entry(comparison, key, region, reviewer, group)
    pair = verify_partial_comparison(comparison)
    with rasterio.open(pair.rgb_path) as rgb:
        _, valid = _rgb_valid_pixels(rgb, pair.rgb_bands, Window(*region['window']))
        if not valid.all():
            raise ValueError('Lernausschnitt enthält ungültige RGB-Pixel; kleineren gültigen Bereich wählen.')
        for geometry in entry['manifest']['geometries']:
            if not _polygon_mask(geometry['polygon_px'], width=valid.shape[1], height=valid.shape[0]).any():
                raise ValueError('Modulumriss enthält keine RGB-Pixel.')
    if data is None:
        data = dict(check=CHECK, fingerprints=comparison.fingerprints, label=comparison.label,
            group_id=group, regions={}, **dict.fromkeys(FALSE_FLAGS, False))
    data['regions'][key] = entry
    if len(data['regions']) > 20:
        raise ValueError('Maximal 20 lokale Lernausschnitte vorbereiten.')
    _write(comparison, key, region, data, previous, should_cancel)
    return entry


def revoke_learning_preparation(comparison, key, *, expected_review_sha256, should_cancel=None):
    """Withdraw completeness without erasing module reviews or other windows."""
    _cancel(should_cancel)
    region = _saved_region(comparison, key)
    if _digest(region) != expected_review_sha256:
        raise ValueError('Modulprüfung wurde geändert; Lernvorbereitung erneut öffnen.')
    data, previous = _read(comparison)
    if data is None or key not in data['regions']:
        return
    del data['regions'][key]
    _write(comparison, key, region, data, previous, should_cancel)


def _write(comparison, key, region, data, previous, should_cancel):
    encoded = _json(data)
    if len(encoded.encode('utf-8')) > 4_000_000:
        raise ValueError('Lokale Lernvorbereitung ist zu groß.')
    target = comparison.folder / STATE
    temporary = comparison.folder / ('pv-learning-' + uuid4().hex + '.LOCAL.next.json')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(encoded)
        _cancel(should_cancel)
        if _saved_region(comparison, key) != region or _read(comparison)[1] != previous:
            raise ValueError('Modulprüfung oder Lernvorbereitung wurde geändert; erneut öffnen.')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
