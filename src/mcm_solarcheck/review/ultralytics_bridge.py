"""Dependency-light bridge from Ultralytics result objects to Phase 7 evidence."""
from __future__ import annotations

from collections.abc import Mapping

from .yolo_adapter import YoloDetection


def detections_from_ultralytics(result: object) -> tuple[YoloDetection, ...]:
    """Translate one Ultralytics result without making it authoritative."""
    names=getattr(result, "names", None)
    boxes=getattr(result, "boxes", None)
    if not isinstance(names, Mapping) or boxes is None:
        raise ValueError("Ultralytics result must expose names and boxes")

    cls_values=_tolist(getattr(boxes, "cls", None))
    conf_values=_tolist(getattr(boxes, "conf", None))
    xyxy_values=_tolist(getattr(boxes, "xyxy", None))
    if not (len(cls_values) == len(conf_values) == len(xyxy_values)):
        raise ValueError("Ultralytics box fields must have equal lengths")

    detections=[]
    for class_id,confidence,box in zip(cls_values,conf_values,xyxy_values):
        index=int(class_id)
        if float(index) != float(class_id) or index not in names:
            raise ValueError("Ultralytics class id is invalid or unknown")
        coords=tuple(float(v) for v in box)
        if len(coords) != 4:
            raise ValueError("Ultralytics xyxy box must contain four coordinates")
        detections.append(YoloDetection(str(names[index]), float(confidence), coords))
    return tuple(detections)


def _tolist(value: object) -> list:
    if value is None:
        raise ValueError("Ultralytics box field is missing")
    if hasattr(value, "detach"):
        value=value.detach()
    if hasattr(value, "cpu"):
        value=value.cpu()
    if hasattr(value, "tolist"):
        value=value.tolist()
    if not isinstance(value, list):
        raise ValueError("Ultralytics box field cannot be converted to a list")
    return value


def infer_ultralytics(model: object, image: object, *, confidence: float = 0.25) -> tuple[YoloDetection, ...]:
    """Run an injected Ultralytics-compatible model and normalize one image result."""
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("inference confidence must be between 0 and 1")
    predict=getattr(model, "predict", None)
    if not callable(predict):
        raise ValueError("model must expose a callable predict method")
    results=predict(source=image, conf=float(confidence), verbose=False)
    if not isinstance(results, (list, tuple)) or len(results) != 1:
        raise ValueError("single-image inference must return exactly one result")
    return detections_from_ultralytics(results[0])
