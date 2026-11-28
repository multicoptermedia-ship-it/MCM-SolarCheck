"""Fixed OpenCV feature-region growth and raster instance validation, no labels in decoding."""
import cv2
import numpy as np

PROFILE = dict(id='pvis-embedding-fixedrange-256-1', foreground_probability=.5,
    embedding_linf_radius=.5, connectivity=8, minimum_region_pixels=16,
    maximum_regions=512, maximum_candidates=128, mask_iou=.5,
    seeds='raster_order', matching='maximum_cardinality_iou_ge_050',
    ignore_policy='decode_without_reference_then_score_only_valid_pixels')


def describe(mask):
    result = []
    for identity in np.unique(mask[mask > 0]):
        y, x = np.nonzero(mask == identity)
        result.append(dict(id=int(identity), area_pixels=len(x),
            bbox=[int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)],
            touches_crop_edge=bool(x.min() == 0 or y.min() == 0
                                  or x.max() == mask.shape[1]-1 or y.max() == mask.shape[0]-1)))
    return result


def decode(logits, *, should_cancel=lambda: False):
    """L-infinity fixed-seed tolerance, no reference mask/count/ignore input.

    FLOODFILL_FIXED_RANGE compares each included pixel with the seed. Floating
    range would chain distinct embeddings through a gradual bridge. Spatially
    disconnected regions stay separate even if their embeddings are equal.
    Limits produce an explicitly UNSCORED crop, never a partial quality score.
    """
    if (not isinstance(logits, np.ndarray) or logits.dtype != np.float32
            or logits.ndim != 3 or logits.shape[0] != 4
            or logits.shape[1:] not in ((64, 64), (256, 256)) or not np.isfinite(logits).all()):
        raise ValueError('Finite four-channel bounded float32 logits required')
    shifted = logits[:2].astype(np.float64)-logits[:2].max(axis=0)
    exp = np.exp(shifted)
    probability = (exp[1]/exp.sum(axis=0)).astype(np.float32)
    remaining = probability >= PROFILE['foreground_probability']
    result = np.zeros(remaining.shape, np.int32)
    # OpenCV accepts float32 1/3-channel images; third feature is exactly zero.
    features = np.zeros((*remaining.shape, 3), np.float32)
    features[:, :, :2] = logits[2:].transpose(1, 2, 0)
    barrier = np.pad((~remaining).astype(np.uint8), 1, constant_values=1)
    flags = cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | 8 | (2 << 8)
    regions, rejected, accepted = 0, 0, 0
    status = 'complete'
    while np.any(remaining):
        if should_cancel(): raise KeyboardInterrupt
        if regions >= PROFILE['maximum_regions'] or accepted >= PROFILE['maximum_candidates']:
            status = 'limit_exceeded_unscored'; break
        index = int(np.flatnonzero(remaining)[0]); y, x = divmod(index, remaining.shape[1])
        radius = (PROFILE['embedding_linf_radius'],)*3
        area, _, _, _ = cv2.floodFill(features, barrier, (x, y), (0.,)*3, radius, radius, flags)
        selected = barrier[1:-1, 1:-1] == 2
        if area != np.count_nonzero(selected) or area < 1: raise ValueError('Invalid OpenCV region')
        regions += 1
        remaining[selected] = False; barrier[1:-1, 1:-1][selected] = 1
        if area < PROFILE['minimum_region_pixels']: rejected += 1; continue
        accepted += 1; result[selected] = accepted
    return result, probability, dict(status=status, foreground_pixels=int((probability >= .5).sum()),
        regions_examined=regions, rejected_small_regions=rejected, candidate_instances=accepted,
        candidates=describe(result))


def score_instances(reference, prediction):
    """Mask IoU on known pixels only; standard maximum-cardinality bipartite match."""
    if (reference.shape != prediction.shape or reference.ndim != 2
            or reference.dtype != np.int32 or prediction.dtype != np.int32
            or reference.min() < -1 or prediction.min() < 0 or reference.max() > 10000
            or prediction.max() > 128 or not np.any(reference >= 0)):
        raise ValueError('Bounded reference and prediction instance rasters required')
    valid = reference >= 0
    refs = np.unique(reference[reference > 0]); preds = np.unique(prediction[valid & (prediction > 0)])
    if len(refs) > 128: raise ValueError('Too many reference instances')
    ref_area = {int(i): int((reference == i).sum()) for i in refs}
    pred_area = {int(i): int(((prediction == i) & valid).sum()) for i in preds}
    ious = {}
    for a in refs:
        observed, intersections = np.unique(prediction[reference == a], return_counts=True)
        for b, intersection in zip(observed, intersections):
            if b > 0:
                iou = int(intersection)/(ref_area[int(a)]+pred_area[int(b)]-int(intersection))
                if iou >= PROFILE['mask_iou']: ious[int(a), int(b)] = iou
    adjacency = {int(a): sorted((int(b) for b in preds if (int(a), int(b)) in ious),
        key=lambda b: (-ious[int(a), b], b)) for a in refs}
    owners = {}
    def augment(a, visited):
        for b in adjacency[a]:
            if b in visited: continue
            visited.add(b)
            if b not in owners or augment(owners[b], visited):
                owners[b] = a; return True
        return False
    for a in refs: augment(int(a), set())
    matches = [dict(reference_id=a, prediction_id=b, iou=ious[a, b]) for b, a in sorted(owners.items())]
    positive = prediction > 0; truth = reference > 0
    result = dict(reference_instances=len(refs), scored_prediction_instances=len(preds),
        predictions_wholly_ignored=len(np.unique(prediction[positive]))-len(preds),
        matched_instances=len(matches), additional_predictions=len(preds)-len(matches),
        missed_references=len(refs)-len(matches),
        foreground_intersection=int((positive & truth & valid).sum()),
        foreground_union=int(((positive | truth) & valid).sum()), matches=matches)
    return result


def aggregate(scores):
    keys = ('reference_instances', 'scored_prediction_instances', 'predictions_wholly_ignored',
        'matched_instances', 'additional_predictions', 'missed_references',
        'foreground_intersection', 'foreground_union')
    result = {k: sum(s[k] for s in scores) for k in keys}
    tp, fp, fn = (result[k] for k in ('matched_instances', 'additional_predictions', 'missed_references'))
    result.update(precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None,
        f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
        foreground_iou=result['foreground_intersection']/result['foreground_union'] if result['foreground_union'] else None,
        count_difference=result['scored_prediction_instances']-result['reference_instances'])
    return result
