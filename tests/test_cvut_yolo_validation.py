"""Synthetic whole-module geometry, overlap matching and alignment regressions."""
import numpy as np
import pytest

from mcm_solarcheck.vision import cvut_yolo_validation as validation


def rectangle(x=40, y=40, width=80, height=40):
    mask = np.zeros((256,256), bool)
    mask[y:y+height,x:x+width] = True
    return mask


def test_overlapping_duplicates_match_one_reference_once():
    mask = rectangle()
    reference = mask.astype(np.int32)
    result = validation.score_masks(reference, np.stack([mask,mask]))
    assert result['matched_instances'] == 1
    assert result['additional_predictions'] == 1
    assert result['missed_references'] == 0


def test_unannotated_regions_neither_become_errors_nor_true_negatives():
    mask, unknown = rectangle(), rectangle(150,150,60,30)
    reference = mask.astype(np.int32)
    reference[unknown] = -1
    result = validation.score_masks(reference, np.stack([mask,unknown]))
    assert result['matched_instances'] == 1
    assert result['predictions_wholly_ignored'] == 1
    assert result['additional_predictions'] == 0


def test_mask_fragments_of_same_instance_stay_one_module():
    mask = rectangle()
    mask[:,78:82] = False
    result = validation.module_masks(np.array([[40,40,120,80]],float),
        mask[None], np.array([.9]))
    assert len(result) == 1 and result[0,60,80]


def test_empty_mask_does_not_shift_later_box_or_confidence():
    masks = np.stack([np.zeros((256,256),bool), rectangle()])
    boxes = np.array([[0,0,10,10],[40,40,120,80]],float)
    result = validation.module_masks(boxes,masks,np.array([.25,.95]))
    assert len(result) == 1 and result[0,60,80]


def test_crop_boundary_and_nested_duplicate_do_not_create_more_modules():
    masks = np.stack([rectangle(),rectangle(),rectangle(0,120)])
    boxes = np.array([[40,40,120,80],[40,40,120,80],[0,120,80,160]],float)
    result = validation.module_masks(boxes,masks,np.array([.9,.8,.9]))
    assert len(result) == 1


def test_foreground_union_is_not_an_instance_count():
    truth = np.zeros((256,256),np.int32)
    truth[40:80,40:80] = 1
    truth[40:80,80:120] = 2
    result = validation.score_masks(truth,(truth>0)[None])
    assert result['foreground_intersection'] == result['foreground_union']
    assert result['matched_instances'] == 1 and result['missed_references'] == 1


@pytest.mark.parametrize('bad', [np.zeros((0,64,64),bool),np.zeros((301,256,256),bool),
    np.zeros((1,256,256),np.uint8)])
def test_unbounded_or_untyped_masks_rejected(bad):
    with pytest.raises(ValueError):
        validation.score_masks(np.zeros((256,256),np.int32),bad)
