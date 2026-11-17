"""Bounded local model evaluation against saved reviewed outlines; no replacement."""
from dataclasses import asdict
from hashlib import sha256
import json
import re

from .thermal_partial_comparison import FLAGS, _local, open_partial_comparison, verify_partial_comparison
from .thermal_partial_pv import STATE as MODULE_STATE, active_entries, load_module_review, detect_partial_pv_window
from .orthophoto_pv_modules import OrthophotoPVWindowResult
from ..vision.onnx_module_detector import OnnxModuleDetector
from ..vision.polygon_geometry import convex_polygon_iou

STATE = 'pv-model-comparison.LOCAL.json'
CHECK = 'solarcheck-pv-model-comparison-1'
EXTRA_FLAGS = ('accuracy_verified', 'automatically_accepted', 'physical_module_ids_confirmed')


def _digest(path):
    return sha256(_local(path).read_bytes()).hexdigest()


def _associate(references, proposals):
    # Standard one-to-one greedy IoU association. Saved outlines are a partial
    # reference, not an exhaustive ground-truth inventory of the selected ROI.
    ranked = []
    for i, ref in enumerate(references):
        for j, proposal in enumerate(proposals):
            iou = convex_polygon_iou(ref['proposal']['rgb_polygon_px'], proposal.rgb_polygon_px)
            if iou >= .5:
                ranked.append((iou, i, j))
    used_refs, used_candidates, matches = set(), set(), []
    for iou, i, j in sorted(ranked, reverse=True):
        if i not in used_refs and j not in used_candidates:
            used_refs.add(i)
            used_candidates.add(j)
            matches.append(dict(reference_id=references[i]['module_id'], candidate_index=j, iou=iou))
    return matches


def compare_saved_region(source, manifest_path, key, *, run_token=None):
    if run_token is not None and not re.fullmatch('[0-9a-f]{32}', run_token):
        raise ValueError('Ungueltiger lokaler Vergleichslauf.')
    comparison = open_partial_comparison(source)
    regions, _ = load_module_review(comparison)
    if key not in regions:
        raise ValueError('Zuerst den ausgewaehlten Modulausschnitt lokal speichern.')
    references = [e for e in active_entries(regions[key]) if e['status'] == 'outline_ok']
    if not references:
        raise ValueError('Mindestens einen gespeicherten Umriss als passend beurteilen.')
    review_sha = _digest(comparison.folder / MODULE_STATE)
    model = OnnxModuleDetector(manifest_path)
    candidate = detect_partial_pv_window(comparison, window=tuple(regions[key]['window']), detector=model)
    matches = _associate(references, candidate.proposals)
    if review_sha != _digest(comparison.folder / MODULE_STATE):
        raise ValueError('Gespeicherte Modulpruefung waehrend des Vergleichs veraendert.')
    verify_partial_comparison(comparison)
    record = dict(check=CHECK, label=comparison.label, fingerprints=comparison.fingerprints,
        review_sha256=review_sha, region=key, window=list(candidate.rgb_window),
        model=model.description, detector=candidate.detector_name,
        references=[dict(module_id=e['module_id'], polygon=e['proposal']['rgb_polygon_px']) for e in references],
        proposals=[asdict(p) for p in candidate.proposals], matches=matches,
        counts=dict(reviewed_outlines=len(references), candidate_outlines=len(candidate.proposals),
            matched_reviewed_outlines=len(matches), unmatched_reviewed_outlines=len(references)-len(matches),
            additional_unreviewed_candidates=len(candidate.proposals)-len(matches)),
        **dict.fromkeys((*FLAGS, *EXTRA_FLAGS), False))
    target = comparison.folder / (f'pv-model-comparison-{run_token}.LOCAL.json' if run_token else STATE)
    temporary = target.with_suffix('.next.json')
    if target.is_symlink() or temporary.is_symlink():
        raise ValueError('Vergleichsbericht darf keine Verknuepfung sein.')
    encoded = json.dumps(record, indent=2, ensure_ascii=False)
    if len(encoded.encode('utf-8')) > 16*1024*1024:
        raise ValueError('Vergleichsbericht zu gross; kleineren Ausschnitt verwenden.')
    temporary.write_text(encoded, encoding='utf-8')
    temporary.replace(target)
    return record


def read_model_comparison(comparison, path=None):
    """Reopen the saved result without loading a model or running inference."""
    path = _local(path or comparison.folder / STATE)
    if path.stat().st_size > 16*1024*1024:
        raise ValueError('Vergleichsbericht zu gross.')
    data = json.loads(path.read_text(encoding='utf-8'))
    if (data.get('check') != CHECK or data.get('fingerprints') != comparison.fingerprints
            or data.get('label') != comparison.label
            or data.get('review_sha256') != _digest(comparison.folder / MODULE_STATE)
            or any(data.get(k) is not False for k in (*FLAGS, *EXTRA_FLAGS))
            or data.get('model', {}).get('production_approved') is not False):
        raise ValueError('Vergleich passt nicht mehr zu Quellen oder gespeicherten Umrissen.')
    regions, _ = load_module_review(comparison)
    key = data['region']
    if key not in regions or data['window'] != regions[key]['window'] or len(data['proposals']) > 2000:
        raise ValueError('Ungueltiger Vergleichsausschnitt.')
    from .thermal_partial_pv import _snapshot
    proposals = []
    for p in data['proposals']:
        proposal, _ = _snapshot(dict(proposal=p, status='pending', note=''), tuple(data['window']))
        proposals.append(proposal)
    # Rebuild the visual reference from the verified review, not report polygons.
    references = [e for e in active_entries(regions[key]) if e['status'] == 'outline_ok']
    matches = _associate(references, proposals)
    counts = dict(reviewed_outlines=len(references), candidate_outlines=len(proposals),
        matched_reviewed_outlines=len(matches), unmatched_reviewed_outlines=len(references)-len(matches),
        additional_unreviewed_candidates=len(proposals)-len(matches))
    if data['counts'] != counts or data['matches'] != matches:
        raise ValueError('Gespeicherte Vergleichszaehler stimmen nicht mit den Umrissen ueberein.')
    return data, OrthophotoPVWindowResult(tuple(proposals), tuple(data['window']), data['detector']), references
