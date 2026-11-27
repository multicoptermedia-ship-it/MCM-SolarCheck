"""Public research scoring; no reference labels enter inference or proposals."""
import cv2
import numpy as np

from .detection import ModuleDetection
from .module_quality import filter_module_detections
from ..services.orthophoto_pv_modules import _polygon_mask

PROFILE = dict(id='cvut-yolov8-public-native512-area256-1', input_size=256,
    rgb='uint8_div255', confidence=.25, box_nms_iou=.7, maximum_predictions=300,
    masks='retina_native_then_min_area_rectangle_of_all_same_instance_pixels',
    minimum_mask_pixels=16, minimum_fill=.5, minimum_aspect=1.25,
    maximum_aspect=2.8, polygon_duplicate_iou=.5, reference_mask_iou=.5,
    boundary='reject_box_or_mask_touching_crop_edge',
    matching='maximum_cardinality_on_known_pixels_only')


def score_masks(reference, masks, *, size=256):
    """Retain overlapping predicted instances, match each reference at most once."""
    if (type(size) is not int or size not in (256,512)
            or not isinstance(reference, np.ndarray) or reference.dtype != np.int32
            or reference.shape != (size,size) or reference.min() < -1
            or reference.max() > 10000 or not np.any(reference >= 0)
            or not isinstance(masks, np.ndarray) or masks.dtype != np.bool_
            or masks.ndim != 3 or masks.shape[1:] != reference.shape or len(masks) > 300):
        raise ValueError('Bounded public reference and boolean instance masks required')
    valid = reference >= 0
    refs = np.unique(reference[reference > 0])
    if len(refs) > 128:
        raise ValueError('Bounded public reference instance count required')
    keep = masks[:, valid].any(axis=1)
    predictions = masks[keep]
    areas = predictions[:, valid].sum(axis=1)
    adjacency = {}
    for identity in refs:
        intersection = predictions[:, reference == identity].sum(axis=1)
        iou = intersection/np.maximum(1, (reference == identity).sum()+areas-intersection)
        adjacency[int(identity)] = sorted(np.flatnonzero(iou >= .5).tolist(),
            key=lambda index: (-iou[index], index))
    owners = {}
    def match(identity, seen):
        for index in adjacency[identity]:
            if index in seen:
                continue
            seen.add(index)
            if index not in owners or match(owners[index], seen):
                owners[index] = identity
                return True
        return False
    for identity in refs:
        match(int(identity), set())
    positive, truth = masks.any(axis=0), reference > 0
    return dict(reference_instances=len(refs), scored_prediction_instances=len(predictions),
        predictions_wholly_ignored=int((~keep).sum()), matched_instances=len(owners),
        additional_predictions=len(predictions)-len(owners), missed_references=len(refs)-len(owners),
        foreground_intersection=int((positive & truth & valid).sum()),
        foreground_union=int(((positive | truth) & valid).sum()))


def module_masks(boxes, masks, confidence):
    """All fragments of one instance form one rectangle; never combine instances."""
    if (boxes.shape != (len(masks),4) or confidence.shape != (len(masks),)
            or masks.dtype != np.bool_ or masks.shape[1:] != (256,256)
            or len(masks) > 300 or not np.isfinite(boxes).all()
            or not np.isfinite(confidence).all() or np.any((confidence < 0) | (confidence > 1))):
        raise ValueError('Aligned bounded decoded public predictions required')
    proposals = []
    for box, mask, probability in zip(boxes, masks, confidence):
        if min(box[:2]) <= 0 or max(box[2:]) >= 256:
            continue
        y, x = np.nonzero(mask)
        if len(x) < 16 or min(x.min(), y.min()) == 0 or max(x.max(), y.max()) == 255:
            continue
        rectangle = cv2.minAreaRect(np.column_stack((x,y)).astype(np.float32))
        a, b = rectangle[1]
        if (min(a,b) <= 0 or not 1.25 <= max(a,b)/min(a,b) <= 2.8
                or len(x)/max(1,a*b) < .5):
            continue
        polygon = tuple(tuple(float(v) for v in p) for p in cv2.boxPoints(rectangle))
        proposals.append(ModuleDetection(polygon, float(probability)))
    proposals = filter_module_detections(tuple(proposals), 256, 256, duplicate_iou=.5)
    return np.stack([_polygon_mask(p.polygon_px, width=256, height=256)
                     for p in proposals]) if proposals else np.zeros((0,256,256), bool)


def infer(torch, model, rgb, *, size=256):
    """Fixed reference decoder; no labels, count, ignore regions or local notes."""
    from ultralytics.utils import ops
    if type(size) is not int or size not in (256,512) or rgb.shape != (size,size,3) or rgb.dtype != np.uint8:
        raise ValueError('Explicit public256 or native512 RGB required')
    with torch.inference_mode():
        x = torch.from_numpy(rgb.transpose(2,0,1).copy()).float().div(255).unsqueeze(0)
        result = model.eval()(x)
        detection = ops.non_max_suppression(result[0], conf_thres=.25, iou_thres=.7,
            nc=1, max_det=300, max_time_img=10)[0]
        if len(detection) >= 300:
            raise ValueError('Public prediction limit reached; crop remains unscored')
        masks = (ops.process_mask_native(result[1][-1][0], detection[:,6:], detection[:,:4],
            (size,size)).cpu().numpy().astype(bool) if len(detection)
            else np.zeros((0,size,size),bool))
        # Do not remove empty masks independently from their boxes/confidences.
        return detection[:,:4].cpu().numpy(), masks, detection[:,4].cpu().numpy()
