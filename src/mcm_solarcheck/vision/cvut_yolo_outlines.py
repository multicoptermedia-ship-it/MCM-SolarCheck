"""Explicit projective public-research outlines, separate from old profiles.

A projected module has no fixed pixel aspect ratio. A tight ROI can contain
one large module. Keep default fallback-detector geometry policy unchanged.
"""
import cv2
import numpy as np

from .detection import ModuleDetection
from .module_quality import filter_module_detections
from ..services.orthophoto_pv_modules import _polygon_mask

PROFILE = dict(id='cvut-yolo-public-projective-quad-1',
    shape='same_instance_convex_hull_approx_polygon_2percent_else_min_area_rectangle',
    minimum_fill=.5, physical_aspect_ratio_assumed=False,
    minimum_mask_pixels_at_256=16, maximum_roi_area_fraction=1.,
    polygon_duplicate_iou=.5, reject_box_or_mask_touching_crop_edge=True,
    coordinates='native_pixel_centers_no_geometric_accuracy_claim')


def projective_outlines(boxes, masks, confidence, *, size=256):
    if (type(size) is not int or size not in (256,512)
            or not isinstance(masks,np.ndarray) or masks.dtype != np.bool_
            or masks.ndim != 3 or masks.shape[1:] != (size,size) or len(masks)>300
            or not isinstance(boxes,np.ndarray) or boxes.shape != (len(masks),4)
            or not isinstance(confidence,np.ndarray) or confidence.shape != (len(masks),)
            or not np.isfinite(boxes).all() or not np.isfinite(confidence).all()
            or np.any(boxes[:,2:]<=boxes[:,:2])
            or np.any((confidence<0)|(confidence>1))):
        raise ValueError('Aligned bounded explicit public instance predictions required')
    result, rejected = [], dict(empty_or_small=0,boundary=0,fill=0,geometry_or_duplicate=0)
    for box, mask, probability in zip(boxes,masks,confidence):
        y,x = np.nonzero(mask)
        if len(x)<16*(size//256)**2:
            rejected['empty_or_small']+=1
            continue
        if (min(box[:2])<=0 or max(box[2:])>=size or min(x.min(),y.min())==0
                or max(x.max(),y.max())==size-1):
            rejected['boundary']+=1
            continue
        hull = cv2.convexHull(np.column_stack((x,y)).astype(np.float32))
        polygon = cv2.approxPolyDP(hull,.02*cv2.arcLength(hull,True),True)
        if len(polygon)!=4 or not cv2.isContourConvex(polygon):
            polygon = cv2.boxPoints(cv2.minAreaRect(hull))
        polygon = polygon.reshape(-1,2)
        area = abs(cv2.contourArea(polygon))
        if area<=0 or len(x)/area<.5:
            rejected['fill']+=1
            continue
        result.append(ModuleDetection(tuple(tuple(float(v) for v in p) for p in polygon),float(probability)))
    kept = filter_module_detections(tuple(result),size,size,duplicate_iou=.5,
        minimum_area_fraction=16/256**2,maximum_area_fraction=1.)
    rejected['geometry_or_duplicate'] = len(result)-len(kept)
    rasters = np.stack([_polygon_mask(d.polygon_px,width=size,height=size) for d in kept]) if kept else np.zeros((0,size,size),bool)
    diagnostics = dict(input_instances=len(masks),accepted_outlines=len(kept),rejected=rejected)
    assert len(masks)==len(kept)+sum(rejected.values())
    return rasters,kept,diagnostics
