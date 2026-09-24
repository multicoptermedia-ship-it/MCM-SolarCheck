"""Backend adapter for reviewed detection geometry in YOLO label format."""
from __future__ import annotations


def yolo_detection_line(defect_class: str, class_ids: dict[str,int], box_xyxy, width: int, height: int) -> str:
    if defect_class not in class_ids:
        raise ValueError(f"defect class has no YOLO class id: {defect_class}")
    class_id=class_ids[defect_class]
    if not isinstance(class_id,int) or isinstance(class_id,bool) or class_id < 0:
        raise ValueError("YOLO class id must be a non-negative integer")
    if not isinstance(width,int) or isinstance(width,bool) or width <= 0 or not isinstance(height,int) or isinstance(height,bool) or height <= 0:
        raise ValueError("YOLO source dimensions must be positive integers")
    if box_xyxy is None or len(box_xyxy)!=4:
        raise ValueError("YOLO detection export requires a reviewed box")
    x1,y1,x2,y2=(float(v) for v in box_xyxy)
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1 or x2 > width or y2 > height:
        raise ValueError("YOLO detection box lies outside source image bounds")
    cx=((x1+x2)/2)/width; cy=((y1+y2)/2)/height
    bw=(x2-x1)/width; bh=(y2-y1)/height
    return f"{class_id} {cx:.10f} {cy:.10f} {bw:.10f} {bh:.10f}"
