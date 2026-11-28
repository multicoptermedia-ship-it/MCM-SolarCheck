"""Synthetic projected shapes and explicit scale; no reference/model training."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.vision.cvut_yolo_outlines import projective_outlines
from mcm_solarcheck.vision import cvut_yolo_validation as old
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_quality import filter_module_detections


def one(polygon,size=256):
    mask=np.zeros((size,size),np.uint8)
    cv2.fillPoly(mask,[np.asarray(polygon,np.int32)],1)
    x,y,w,h=cv2.boundingRect(np.asarray(polygon,np.int32))
    return np.array([[x,y,x+w,y+h]],float),mask[None].astype(bool),np.array([.9])


@pytest.mark.parametrize('polygon',[
    [(40,40),(210,40),(200,65),(45,65)],
    [(40,40),(140,40),(140,140),(40,140)],
    [(40,40),(210,70),(180,120),(55,110)],
    [(20,20),(230,20),(230,230),(20,230)],
])
def test_projected_modules_need_no_fixed_aspect_or_small_roi_fraction(polygon):
    boxes,masks,scores=one(polygon)
    result,polygons,diagnostics=projective_outlines(boxes,masks,scores)
    assert len(result)==len(polygons)==1
    assert diagnostics['accepted_outlines']==1
    intersection=(result[0]&masks[0]).sum()
    # Pixel-center rasterization and a 2% contour approximation can lose a
    # small boundary strip, especially on the thin projected test module.
    assert intersection/(result[0]|masks[0]).sum()>.85


def test_default_fallback_size_policy_is_preserved():
    detection=ModuleDetection(((20.,20.),(230.,20.),(230.,230.),(20.,230.)),.9)
    assert filter_module_detections((detection,),256,256)==()
    assert filter_module_detections((detection,),256,256,maximum_area_fraction=1.)==(detection,)


@pytest.mark.parametrize('limits',[(.5,.2),(-.1,1.),(0,1.1),(0,float('nan'))])
def test_invalid_explicit_size_limits_rejected(limits):
    with pytest.raises(ValueError):
        filter_module_detections((),256,256,minimum_area_fraction=limits[0],
            maximum_area_fraction=limits[1])


def test_empty_masks_keep_boxes_aligned_and_same_instance_fragments_together():
    boxes,masks,scores=one([(40,40),(160,40),(160,100),(40,100)])
    masks[0,:,98:102]=False
    masks=np.concatenate([np.zeros_like(masks),masks])
    result,_,diag=projective_outlines(np.concatenate([[[1,1,3,3]],boxes]),masks,
        np.array([.25,.9]))
    assert len(result)==1 and result[0,70,100]
    assert diag['rejected']['empty_or_small']==1


def test_border_modules_and_duplicate_instances_remain_rejected():
    boxes,masks,scores=one([(40,40),(160,40),(160,100),(40,100)])
    border=one([(0,140),(120,140),(120,200),(0,200)])
    result,_,diag=projective_outlines(np.concatenate([boxes,boxes,border[0]]),
        np.concatenate([masks,masks,border[1]]),np.array([.9,.8,.9]))
    assert len(result)==1
    assert diag['rejected']['boundary']==diag['rejected']['geometry_or_duplicate']==1


def test_native512_is_explicit_and_uses_matching_pixel_area():
    boxes,masks,scores=one([(80,80),(320,80),(300,180),(90,180)],512)
    with pytest.raises(ValueError):projective_outlines(boxes,masks,scores)
    result,_,_=projective_outlines(boxes,masks,scores,size=512)
    reference=masks[0].astype(np.int32)
    with pytest.raises(ValueError):old.score_masks(reference,result)
    assert old.score_masks(reference,result,size=512)['matched_instances']==1


def test_all_rejection_counts_account_for_input_instances():
    _,_,diag=projective_outlines(np.zeros((0,4)),np.zeros((0,256,256),bool),np.zeros(0))
    assert diag['input_instances']==diag['accepted_outlines']+sum(diag['rejected'].values())==0


def test_inverted_boxes_are_rejected_before_geometry():
    boxes,masks,scores=one([(40,40),(160,40),(160,100),(40,100)])
    boxes[0,[0,2]]=boxes[0,[2,0]]
    with pytest.raises(ValueError):projective_outlines(boxes,masks,scores)
