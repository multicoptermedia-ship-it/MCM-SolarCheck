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
from .orthophoto_pv_modules import _cancel, _rgb_valid_pixels, _polygons_mask
from ..review.training_geometry import ReviewedGeometry, validate_geometry_bounds
from ..review.training_snapshot import TrainingSnapshot
from ..review.training_export import build_spatial_training_index
from ..vision.polygon_geometry import convex_polygon_iou

STATE = 'pv-learning-preparation.LOCAL.json'
CHECK = 'solarcheck-pv-learning-preparation-2'
LEGACY_CHECK = 'solarcheck-pv-learning-preparation-1'
MASK_POLICY = 'whole-pv1-background0-ignore255-margin1-1'
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
    if (not isinstance(data, dict) or data.get('check') not in (CHECK, LEGACY_CHECK)
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
                or entry['manifest'].get('mask_policy', MASK_POLICY) != MASK_POLICY
                or (data['check'] == LEGACY_CHECK and 'mask_policy' in entry['manifest'])
                or any(entry['manifest'].get(k) is not False for k in FALSE_FLAGS)):
            raise ValueError('Ungültiger gespeicherter Lernmusterstand.')
    return data, raw


def annotation_problem(region, ignored_ids=()):
    entries = [e for e in active_entries(region) if e['module_id'] not in ignored_ids]
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


def validate_ignore_areas(window, areas):
    """Exclusion boundaries, never asserted physical module corners; ROI local."""
    if not isinstance(areas, (tuple, list)) or len(areas) > 20:
        raise ValueError('Maximal 20 unklare Bereiche je Ausschnitt markieren.')
    width, height = window[2:]
    normalized = []
    for area in areas:
        if (not isinstance(area, (list, tuple)) or len(area) != 4
                or any(not isinstance(p, (list, tuple)) or len(p) != 2
                    or any(type(v) not in (int, float) or not np.isfinite(v) for v in p) for p in area)):
            raise ValueError('Vier gültige Bereichsecken innerhalb des Ausschnitts erforderlich.')
        polygon = tuple(tuple(float(v) for v in p) for p in area)
        points = np.asarray(polygon, dtype=np.float32)
        if (not cv2.isContourConvex(points) or abs(cv2.contourArea(points)) < 1
                or any(x < 0 or y < 0 or x > width-1 or y > height-1 for x, y in polygon)):
            raise ValueError('Einen konvexen unklaren Bereich innerhalb des Ausschnitts markieren.')
        normalized.append(polygon)
    return tuple(normalized)


def _selection(region, areas):
    areas = validate_ignore_areas(region['window'], areas)
    col, row, _, _ = region['window']
    candidates = [(e, tuple((float(x-col), float(y-row)) for x, y in e['proposal']['rgb_polygon_px']))
        for e in active_entries(region) if e['status'] != 'rejected']
    ignored = {e['module_id'] for e, polygon in candidates
        if any(convex_polygon_iou(polygon, area) > 0 for area in areas)}
    # Include whole intersected proposals, including nested false fragments.
    # No guessed module geometry becomes a positive target through this path.
    changed = True
    while changed:
        changed = False
        excluded = [polygon for e, polygon in candidates if e['module_id'] in ignored]
        for entry, polygon in candidates:
            if entry['module_id'] not in ignored and any(_overlapping(polygon, p) for p in excluded):
                ignored.add(entry['module_id'])
                changed = True
    effective = (*areas, *(p for e, p in candidates if e['module_id'] in ignored))
    return areas, ignored, effective


def learning_selection(comparison, key, ignore_areas=()):
    region = _saved_region(comparison, key)
    areas, ignored, _ = _selection(region, ignore_areas)
    return dict(ignore_areas=areas, ignored_count=len(ignored),
        problem=annotation_problem(region, ignored),
        module_count=sum(e['status'] == 'outline_ok' and e['module_id'] not in ignored for e in active_entries(region)))


def _entry(comparison, key, region, reviewer, group, ignore_areas=(), *, mask_policy=True):
    areas, ignored, effective = _selection(region, ignore_areas)
    problem = annotation_problem(region, ignored)
    if problem:
        raise ValueError(problem)
    col, row, width, height = region['window']
    frame = 'RGB-' + comparison.fingerprints['rgb'] + ':' + key
    labels, geometries, polygons = [], [], []
    for entry in active_entries(region):
        if entry['status'] != 'outline_ok' or entry['module_id'] in ignored:
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
    if mask_policy:
        manifest.update(mask_policy=MASK_POLICY, user_ignore_polygons_px=areas,
            ignore_polygons_px=effective, ignored_draft_ids=sorted(ignored))
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
    areas = entry['manifest'].get('user_ignore_polygons_px', ()) if entry else ()
    needs_mask_review = bool(entry and 'mask_policy' not in entry['manifest'])
    if current and _json(_entry(comparison, key, region, entry['reviewer'], data['group_id'], areas,
            mask_policy=not needs_mask_review)) != _json(entry):
        raise ValueError('Lernmuster passen nicht zu den gespeicherten Modulkorrekturen.')
    _, ignored, _ = _selection(region, areas)
    return dict(group_id=data['group_id'] if data else '', entry=entry, current=current, review_sha256=_digest(region),
        ignore_areas=areas, needs_mask_review=needs_mask_review, ignored_count=len(ignored),
        problem=annotation_problem(region, ignored),
        module_count=sum(e['status'] == 'outline_ok' and e['module_id'] not in ignored for e in active_entries(region)))


def learning_index(entry):
    """Metadata index: polygons address the explicit source window, not full TIFF.

    This does not export raster crops or authorize a trainer to consume them.
    """
    manifest = entry['manifest']
    snapshot = TrainingSnapshot(entry['snapshot_id'], 1, len(manifest['labels']), _json(manifest))
    return tuple(dict(row, source_window=manifest['samples'][0]['source_window'],
        geometry_coordinate_frame='source_window', mask_policy=manifest.get('mask_policy'),
        ignore_polygons_px=manifest.get('ignore_polygons_px', ()), ignore_value=255)
        for row in build_spatial_training_index(snapshot, 'segmentation'))


def prepared_split(entry):
    return learning_index(entry)[0]['split']


def save_learning_preparation(comparison, key, *, reviewer, group_id, complete_annotation,
        expected_review_sha256, ignore_areas=(), should_cancel=None):
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
    entry = _entry(comparison, key, region, reviewer, group, ignore_areas)
    target_mask = learning_target(entry)
    learning_target(entry, (480, 270))
    pair = verify_partial_comparison(comparison)
    with rasterio.open(pair.rgb_path) as rgb:
        _, valid = _rgb_valid_pixels(rgb, pair.rgb_bands, Window(*region['window']))
        if np.any(~valid & (target_mask != 255)):
            raise ValueError('Lernausschnitt enthält ungültige RGB-Pixel; kleineren gültigen Bereich wählen.')
    if data is None:
        data = dict(check=CHECK, fingerprints=comparison.fingerprints, label=comparison.label,
            group_id=group, regions={}, **dict.fromkeys(FALSE_FLAGS, False))
    data['check'] = CHECK
    data['regions'][key] = entry
    if len(data['regions']) > 20:
        raise ValueError('Maximal 20 lokale Lernausschnitte vorbereiten.')
    _write(comparison, key, region, data, previous, should_cancel)
    return entry


def learning_target(entry, size=None):
    """In-memory categorical target: 0 background, 1 PV, 255 ignored loss.

    Downsampling exclusions is conservative: any contributing ignored source
    pixel excludes the destination pixel. No model, exports or Celsius data.
    """
    manifest = entry['manifest']
    if manifest.get('mask_policy') != MASK_POLICY:
        raise ValueError('Ältere Vorbereitung zuerst als Lernmaske prüfen und erneut speichern.')
    width, height = manifest['samples'][0]['source_window'][2:]
    target = _polygons_mask([g['polygon_px'] for g in manifest['geometries']], width=width, height=height).astype(np.uint8)
    ignored = _polygons_mask(manifest['ignore_polygons_px'], width=width, height=height).astype(np.uint8)
    ignored = cv2.dilate(ignored, np.ones((3, 3), np.uint8))
    target[ignored > 0] = 255
    if size is not None:
        if (not isinstance(size, tuple) or len(size) != 2
                or any(type(v) is not int or not 1 <= v <= 2048 for v in size)):
            raise ValueError('Begrenzte Zielgröße erforderlich.')
        target = cv2.resize(target, size, interpolation=cv2.INTER_NEAREST_EXACT)
        ignored = cv2.resize(ignored.astype(np.float32), size, interpolation=cv2.INTER_AREA)
        target[ignored > 0] = 255
    if not np.any(target == 1) or not np.any(target == 0):
        raise ValueError('Modulflächen und Hintergrund müssen außerhalb der Ausnahmen auch in der Zielgröße erhalten bleiben.')
    return target


def preview_learning_preparation(comparison, key, *, reviewer, group_id, ignore_areas=(), expected_review_sha256):
    region = _saved_region(comparison, key)
    if _digest(region) != expected_review_sha256:
        raise ValueError('Modulprüfung geändert; Lernvorbereitung erneut öffnen.')
    return _entry(comparison, key, region, _text(reviewer), normalize_group(group_id), ignore_areas)


def learning_counts(entry):
    native, resized = learning_target(entry), learning_target(entry, (480, 270))
    manifest = entry['manifest']
    return dict(check='solarcheck-pv-learning-counts-1', module_outlines=len(manifest['labels']),
        ignored_outlines=len(manifest['ignored_draft_ids']), ignored_areas=len(manifest['user_ignore_polygons_px']),
        split=prepared_split(entry),
        native_pixels={name: int(np.count_nonzero(native == value)) for name, value in (('background', 0), ('pv', 1), ('ignored', 255))},
        candidate_480x270_pixels={name: int(np.count_nonzero(resized == value)) for name, value in (('background', 0), ('pv', 1), ('ignored', 255))},
        original_cvut_profile_verified=False, **dict.fromkeys(FALSE_FLAGS, False))


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
