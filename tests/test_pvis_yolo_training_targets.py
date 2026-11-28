"""Generated whole-object zoom and supervision eligibility contracts."""
import numpy as np
import pytest

from mcm_solarcheck.services import pvis_yolo_training_targets as targets


def source():
    rgb=np.full((256,256,3),180,np.uint8)
    labels=np.zeros((256,256),np.int32)
    labels[17:19,70:110]=1  # no stride8/16/32 center inside the narrow box
    labels[45:90,40:130]=2
    rgb[labels>0]=(30,60,100)
    return rgb,labels


def test_small_module_gains_anchor_support_without_changing_sources():
    rgb,labels=source();a,b=rgb.copy(),labels.copy()
    assert 1 not in targets.supported_instances(labels)
    image,result,info=targets.prepare(rgb,labels,0)
    assert info['zoomed'] and 1 in targets.supported_instances(result)
    assert info['eligible'] and np.array_equal(rgb,a) and np.array_equal(labels,b)
    assert image.shape==rgb.shape and result.dtype==np.int32


def test_partial_module_is_unknown_not_a_new_half_module_target():
    rgb,labels=source()
    _,result,info=targets.prepare(rgb,labels,0)
    assert info['partial_instances_ignored']==1
    assert 2 not in np.unique(result) and np.any(result==-1)


def test_unlearnable_objects_never_become_background_on_unzoomed_steps():
    rgb,labels=source()
    _,result,info=targets.prepare(rgb,labels,1)
    assert info['unsupported_instances_ignored']==1
    assert np.all(result[labels==1]==-1) and 2 in np.unique(result)


def test_crop_without_supported_foreground_is_ineligible_not_confirmed_negative():
    rgb,labels=source();labels[labels==2]=0
    _,result,info=targets.prepare(rgb,labels,1)
    assert not info['eligible'] and not np.any(result>0)


def test_existing_unknown_pixels_survive_resize_and_outputs_are_deterministic():
    rgb,labels=source();labels[:15,:]=-1
    a,b,info=targets.prepare(rgb,labels,0);x,y,same=targets.prepare(rgb,labels,0)
    assert np.array_equal(a,x) and np.array_equal(b,y) and info==same
    assert np.any(b==-1)


@pytest.mark.parametrize('step',[-1,True,1.5,'1'])
def test_bad_step_rejected(step):
    with pytest.raises(ValueError):targets.prepare(*source(),step)


def test_large_module_is_not_cut_to_force_a_zoom():
    rgb=np.zeros((256,256,3),np.uint8);labels=np.zeros((256,256),np.int32)
    labels[20:240,20:240]=1
    _,result,info=targets.prepare(rgb,labels,0)
    assert not info['zoomed'] and info['retained_instances']==1
    assert np.array_equal(labels,result)


def test_regular_supported_modules_keep_the_original_scale():
    rgb=np.zeros((256,256,3),np.uint8);labels=np.zeros((256,256),np.int32)
    labels[40:90,40:130]=1
    image,result,info=targets.prepare(rgb,labels,0)
    assert not info['zoomed'] and np.array_equal(image,rgb) and np.array_equal(result,labels)


def test_narrow_centered_box_can_shift_off_the_gap_between_anchor_centers():
    rgb=np.zeros((256,256,3),np.uint8);labels=np.zeros((256,256),np.int32)
    labels[127:129,80:170]=1
    assert 1 not in targets.supported_instances(labels)
    _,result,info=targets.prepare(rgb,labels,1,force_zoom=True)
    assert info['zoomed'] and 1 in targets.supported_instances(result)
