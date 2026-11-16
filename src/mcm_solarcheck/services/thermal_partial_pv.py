"""Local draft module review on the already selected RGB and incomplete Thermal.

Reuses the existing detector, module normalizer and GIS mapping. Draft IDs are
scoped to a native RGB window; they are not confirmed physical module identities.
"""
from dataclasses import asdict
import json
from math import ceil, floor, isfinite

from .thermal_partial_comparison import STATE as COMPARISON_STATE, FLAGS, _local, verify_partial_comparison
from .orthophoto_pv_modules import (
    OrthophotoPVModuleProposal, OrthophotoPVWindowResult, _detect_orthophoto_pv_pair, _validate_window,
)
from .orthophoto_layer_alignment import aligned_preview_arrays
from ..vision.detection import ModuleDetection, normalize_module_detections
from ..vision.module_quality import filter_module_detections

STATE = 'pv-modules.LOCAL.json'
CHECK = 'solarcheck-incomplete-thermal-pv-drafts-1'
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
    proposals, reviews = [], {}
    for entry in entries:
        p = entry['proposal']
        polygon = _polygon(p['rgb_polygon_px'], 16)
        local = tuple((x-col, y-row) for x, y in polygon)
        raw = ModuleDetection(local, p['confidence'])
        if not filter_module_detections((raw,), width, height):
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
        proposals.append(OrthophotoPVModuleProposal(polygon, _polygon(p['thermal_polygon_px']),
            p['confidence'], coverage, count, total))
        if entry['module_id'] in reviews:
            raise ValueError('Doppelte Entwurfs-ID.')
        reviews[entry['module_id']] = dict(status=entry['status'], note=entry['note'])
    result = OrthophotoPVWindowResult(tuple(proposals), window, data['detector'])
    if draft_module_ids(comparison, result) != tuple(e['module_id'] for e in entries):
        raise ValueError('Gespeicherte Entwurfs-IDs passen nicht zum RGB-Ausschnitt.')
    # This also validates statuses/notes, retaining immutable proposal flags.
    return result, make_region(comparison, result, reviews)


def load_module_review(comparison):
    _ready(comparison)
    path = comparison.folder / STATE
    if not path.exists():
        return {}, None
    with _local(path).open(encoding='utf-8') as stream:
        data = json.load(stream)
    if (not isinstance(data, dict) or data.get('check') != CHECK or data.get('fingerprints') != comparison.fingerprints
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
