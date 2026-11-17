"""Local draft module review on the already selected RGB and incomplete Thermal.

Reuses the existing detector, module normalizer and GIS mapping. Draft IDs are
scoped to a native RGB window; they are not confirmed physical module identities.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from math import ceil, floor, isfinite

import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Transformer

from .thermal_partial_comparison import STATE as COMPARISON_STATE, FLAGS, _local, verify_partial_comparison
from .orthophoto_pv_modules import (
    OrthophotoPVModuleProposal, OrthophotoPVWindowResult, _detect_orthophoto_pv_pair, _validate_window,
    _rgb_valid_pixels, _polygon_mask, _map_polygon, _thermal_coverage, _cancel,
)
from .orthophoto_layer_alignment import aligned_preview_arrays
from ..vision.detection import ModuleDetection, normalize_module_detections
from ..vision.module_quality import filter_module_detections, assess_module_detection
from ..vision.polygon_geometry import convex_polygon_iou

STATE = 'pv-modules.LOCAL.json'
CHECK = 'solarcheck-incomplete-thermal-pv-drafts-2'
LEGACY_CHECK = 'solarcheck-incomplete-thermal-pv-drafts-1'
REVIEWS = ('pending', 'outline_ok', 'rejected')


def _ready(comparison):
    pair = verify_partial_comparison(comparison)
    with _local(comparison.folder / COMPARISON_STATE).open(encoding='utf-8') as stream:
        saved = json.load(stream)
    if (not isinstance(saved, dict) or saved.get('fingerprints') != comparison.fingerprints or saved.get('verdict') != 'looks_aligned'
            or any(saved.get(k) is not False for k in FLAGS)):
        raise ValueError('Zuerst den RGB-/Thermal-Sichtvergleich als passend lokal speichern.')
    return pair


def region_key(window):
    _validate_window(window)
    return '-'.join(str(v) for v in window)


def draft_module_ids(comparison, result):
    # Existing normalizer supplies deterministic labels within one explicit frame.
    frame = 'RGB-' + comparison.fingerprints['rgb'][:12] + ':' + region_key(result.rgb_window)
    modules = normalize_module_detections(frame,
        tuple(ModuleDetection(p.rgb_polygon_px, p.confidence) for p in result.proposals),
        detector_name=result.detector_name, minimum_confidence=0, validate_geometry=False)
    by_polygon = {m.polygon_px: m.module_id for m in modules}
    return tuple(by_polygon[p.rgb_polygon_px] for p in result.proposals)


def detect_partial_pv_window(comparison, *, window, detector=None, should_cancel=None):
    _validate_window(window)
    if should_cancel is not None and should_cancel():
        raise RuntimeError('Modulpruefung abgebrochen.')
    pair = _ready(comparison)
    result = _detect_orthophoto_pv_pair(pair, window=window, detector=detector, should_cancel=should_cancel)
    verify_partial_comparison(comparison)
    return result


def make_region(comparison, result, reviews=None):
    ids = draft_module_ids(comparison, result)
    reviews = reviews or {}
    entries = []
    for module_id, proposal in zip(ids, result.proposals):
        review = reviews.get(module_id, {})
        status, note = review.get('status', 'pending'), review.get('note', '')
        if status not in REVIEWS or not isinstance(note, str) or len(note) > 1000:
            raise ValueError('Ungueltige lokale Modulbeurteilung (maximal 1000 Zeichen).')
        entries.append(dict(module_id=module_id, proposal=asdict(proposal), status=status, note=note))
    return dict(window=list(result.rgb_window), detector=result.detector_name, entries=entries)


def _polygon(value, maximum=256):
    if (not isinstance(value, (list, tuple)) or not 3 <= len(value) <= maximum
            or any(not isinstance(p, (list, tuple)) or len(p) != 2
                or any(type(v) not in (int, float) or not isfinite(v) for v in p) for p in value)):
        raise ValueError('Ungueltiger gespeicherter Modulumriss.')
    return tuple(tuple(v for v in p) for p in value)


def _snapshot(value, window, *, manual=False):
    """Validate one local revision, including its unapproved proposal flags."""
    col, row, width, height = window
    p = value['proposal']
    polygon = _polygon(p['rgb_polygon_px'], 16)
    local = tuple((x-col, y-row) for x, y in polygon)
    confidence = p['confidence']
    if type(confidence) not in (int, float) or not isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError('Ungueltige Vorschlagskonfidenz.')
    raw = ModuleDetection(local, confidence)
    accepted = (assess_module_detection(raw, width, height, minimum_area_fraction=0,
        maximum_area_fraction=1).accepted if manual else bool(filter_module_detections((raw,), width, height)))
    if not accepted:
        raise ValueError('Ungueltiger gespeicherter RGB-Modulumriss.')
    count, total = p['thermal_valid_pixel_count'], p['thermal_polygon_sample_count']
    coverage = p['thermal_valid_coverage']
    if (any(type(v) is not int for v in (count, total)) or not 0 <= count <= total <= 1_000_000
            or type(coverage) not in (int, float) or not isfinite(coverage)
            or abs(coverage - (count / total if total else 0)) > 1.e-9
            or p.get('review_status') != 'pending'
            or any(p.get(k) is not False for k in ('module_analysis_verified',
                'geometric_registration_verified', 'thermal_calibration_verified'))):
        raise ValueError('Modulvorschlag darf keine Freigabe enthalten.')
    status, note = value['status'], value['note']
    if status not in REVIEWS or not isinstance(note, str) or len(note) > 1000:
        raise ValueError('Ungueltige lokale Modulbeurteilung (maximal 1000 Zeichen).')
    proposal = OrthophotoPVModuleProposal(polygon, _polygon(p['thermal_polygon_px']),
        confidence, coverage, count, total)
    return proposal, dict(proposal=asdict(proposal), status=status, note=note)


def parse_region(comparison, data):
    window = tuple(data['window'])
    _validate_window(window)
    col, row, width, height = window
    pair = comparison._pair
    if col + width > pair.rgb_reference.width or row + height > pair.rgb_reference.height:
        raise ValueError('Gespeicherter Modulausschnitt ausserhalb RGB.')
    entries = data['entries']
    if not isinstance(entries, list) or len(entries) > 2000:
        raise ValueError('Zu viele Modulvorschlaege.')
    proposals, canonical, roots, detected_ids, manual_ids = [], [], [], [], []
    for entry in entries:
        origin, history = entry.get('origin', 'detected'), entry.get('history', [])
        if origin not in ('detected', 'manual') or not isinstance(history, list) or len(history) > 20:
            raise ValueError('Ungueltige lokale Umrisshistorie (maximal 20 Korrekturen).')
        snapshots = []
        for index, old in enumerate(history):
            _, snapshot = _snapshot(old, window, manual=origin == 'manual' or index > 0)
            snapshots.append(snapshot)
        proposal, current = _snapshot(entry, window, manual=origin == 'manual' or bool(history))
        module_id = entry['module_id']
        if not isinstance(module_id, str):
            raise ValueError('Ungueltige Entwurfs-ID.')
        if origin == 'detected':
            if manual_ids:
                raise ValueError('Manuelle Ergaenzungen muessen nach den Detektorentwuerfen stehen.')
            root, _ = _snapshot(history[0] if history else entry, window)
            roots.append(root)
            detected_ids.append(module_id)
        else:
            manual_ids.append(module_id)
        proposals.append(proposal)
        canonical.append(dict(module_id=module_id, **current, origin=origin, history=snapshots))
    baseline = OrthophotoPVWindowResult(tuple(roots), window, data['detector'])
    if draft_module_ids(comparison, baseline) != tuple(detected_ids):
        raise ValueError('Gespeicherte Entwurfs-IDs passen nicht zum RGB-Ausschnitt.')
    frame = 'RGB-' + comparison.fingerprints['rgb'][:12] + ':' + region_key(window)
    expected = tuple(f'{frame}:M-{i:04d}' for i in range(len(roots)+1, len(entries)+1))
    if tuple(manual_ids) != expected or len({e['module_id'] for e in canonical}) != len(entries):
        raise ValueError('Ungueltige oder doppelte manuelle Entwurfs-ID.')
    result = OrthophotoPVWindowResult(tuple(proposals), window, data['detector'])
    return result, dict(window=list(window), detector=data['detector'], entries=canonical)


def manual_module_outline(comparison, region, polygon, *, module_id=None, should_cancel=None):
    """Return a revised region, never writing files or running a detector.

    Native RGB pixel centers, four convex corners in perimeter order. The ID
    and original rejected/accepted revision survive corrections. Additions use
    a new local ID; no detection confidence or physical identity is inferred.
    """
    _cancel(should_cancel)
    pair = _ready(comparison)
    result, updated = parse_region(comparison, region)
    polygon = _polygon(polygon, 4)
    if len(polygon) != 4:
        raise ValueError('Vier Modulecken der Reihe nach markieren.')
    col, row, width, height = result.rgb_window
    local = tuple((x-col, y-row) for x, y in polygon)
    if not assess_module_detection(ModuleDetection(local, 0), width, height,
            minimum_area_fraction=0, maximum_area_fraction=1).accepted:
        raise ValueError('Vier konvexe Modulecken innerhalb des RGB-Ausschnitts markieren.')
    entries = updated['entries']
    old = next((e for e in entries if e['module_id'] == module_id), None)
    if module_id is not None and old is None:
        raise ValueError('Entwurfs-ID nicht in diesem Ausschnitt.')
    if (old is None and len(entries) >= 2000) or (old is not None and len(old['history']) >= 20):
        raise ValueError('Grenze fuer lokale Entwuerfe oder Korrekturen erreicht.')
    for entry in entries:
        if entry is not old and entry['status'] != 'rejected' and convex_polygon_iou(
                polygon, entry['proposal']['rgb_polygon_px']) >= .75:
            raise ValueError('Umriss ueberlappt einen vorhandenen Entwurf; diesen korrigieren oder verwerfen.')
    with rasterio.open(pair.rgb_path) as rgb, rasterio.open(pair.thermal_path) as thermal:
        _, valid = _rgb_valid_pixels(rgb, pair.rgb_bands, Window(*result.rgb_window))
        mask = _polygon_mask(local, width=width, height=height)
        if not mask.any() or np.any(mask & ~valid):
            raise ValueError('Modulumriss enthaelt ungueltige RGB-Pixel.')
        mapped = _map_polygon(polygon, rgb.transform, thermal.transform,
            Transformer.from_crs(rgb.crs, thermal.crs, always_xy=True))
        coverage, count, total = _thermal_coverage(thermal, mapped, pair.thermal_bands, should_cancel)
    proposal = OrthophotoPVModuleProposal(polygon, mapped, 0., coverage, count, total)
    if old is not None:
        old['history'].append(deepcopy({k: old[k] for k in ('proposal', 'status', 'note')}))
        old.update(proposal=asdict(proposal), status='pending')
    else:
        frame = 'RGB-' + comparison.fingerprints['rgb'][:12] + ':' + region_key(result.rgb_window)
        entries.append(dict(module_id=f'{frame}:M-{len(entries)+1:04d}', proposal=asdict(proposal),
            status='pending', note='', origin='manual', history=[]))
    _cancel(should_cancel)
    verify_partial_comparison(comparison)
    return parse_region(comparison, updated)[1]


def load_module_review(comparison):
    _ready(comparison)
    path = comparison.folder / STATE
    if not path.exists():
        return {}, None
    with _local(path).open(encoding='utf-8') as stream:
        data = json.load(stream)
    if (not isinstance(data, dict) or data.get('check') not in (CHECK, LEGACY_CHECK) or data.get('fingerprints') != comparison.fingerprints
            or data.get('label') != comparison.label or not isinstance(data.get('regions'), dict)
            or len(data['regions']) > 20 or any(data.get(k) is not False for k in FLAGS)
            or data.get('physical_module_ids_confirmed') is not False):
        raise ValueError('Ungueltige gespeicherte lokale Modulpruefung.')
    regions = {}
    for key, value in data['regions'].items():
        result, region = parse_region(comparison, value)
        if key != region_key(result.rgb_window):
            raise ValueError('Ungueltige Ausschnittzuordnung.')
        regions[key] = region
    if sum(len(r['entries']) for r in regions.values()) > 2000 or data['last_region'] not in regions:
        raise ValueError('Ungueltiger gespeicherter Modulbereich.')
    return regions, data['last_region']


def save_module_review(comparison, regions, last_region):
    _ready(comparison)
    if not regions or len(regions) > 20 or last_region not in regions:
        raise ValueError('Maximal 20 lokale Ausschnitte speichern.')
    normalized = {}
    for key, value in regions.items():
        result, region = parse_region(comparison, value)
        if key != region_key(result.rgb_window):
            raise ValueError('Ungueltiger Modulbereich.')
        normalized[key] = region
    if sum(len(r['entries']) for r in normalized.values()) > 2000:
        raise ValueError('Maximal 2000 lokale Modul-Entwuerfe speichern.')
    record = dict(check=CHECK, fingerprints=comparison.fingerprints, label=comparison.label,
        regions=normalized, last_region=last_region, physical_module_ids_confirmed=False,
        **dict.fromkeys(FLAGS, False))
    target, temporary = comparison.folder / STATE, comparison.folder / 'pv-modules.LOCAL.next.json'
    if target.is_symlink() or temporary.is_symlink():
        raise ValueError('Modulbericht darf keine Verknuepfung sein.')
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(target)
    return record


def partial_module_detail(comparison, proposal):
    pair = _ready(comparison)
    xs, ys = zip(*proposal.rgb_polygon_px)
    left, top = max(0, floor(min(xs))-2), max(0, floor(min(ys))-2)
    right = min(pair.rgb_reference.width, ceil(max(xs))+3)
    bottom = min(pair.rgb_reference.height, ceil(max(ys))+3)
    window = (left, top, right-left, bottom-top)
    pixels, heat = aligned_preview_arrays(pair, rgb_window=window, max_dimension=512)
    verify_partial_comparison(comparison)
    return pixels, heat
