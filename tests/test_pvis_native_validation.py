"""Exact native/reduced identity and no admission of test/customer sources."""
from io import BytesIO
import numpy as np
from PIL import Image
import pytest

from mcm_solarcheck.services import pvis_native_validation as native
from mcm_solarcheck.services import pvis_image_adapter as pixels
from mcm_solarcheck.services.pvis_public_training_data import training_arrays


def pair():
    rgb=np.full((640,640,3),160,np.uint8)
    rgb[80:200,80:300]=(30,60,100)
    stream=BytesIO();Image.fromarray(rgb).save(stream,format='JPEG')
    image=dict(id=1,width=640,height=640)
    ann=dict(id=1,image_id=1,bbox=[80,80,220,120],
        segmentation=[[80,80,300,80,300,200,80,200]])
    sample=pixels.load_sample(stream.getvalue(),image,[ann],station='033',split='validation',
        window=(0,0,512,512))
    rgb,labels=training_arrays(sample.rgb,sample.instances)
    return sample,rgb,labels


def test_native_pair_preserves_exact_original_rgb_labels_and_record():
    sample,rgb,labels=pair()
    native.verify_native_pair(sample,rgb,labels,sample.record['record_sha256'])


@pytest.mark.parametrize('changed',['rgb','labels','record','station','split'])
def test_changed_source_or_reduction_cannot_silently_change_existing_crop(changed):
    sample,rgb,labels=pair();expected=sample.record['record_sha256']
    if changed=='rgb':rgb[0,0,0]^=1
    elif changed=='labels':labels[70,70]=0
    elif changed=='record':expected='0'*64
    elif changed=='station':sample.record['station']='024'
    else:sample.record['split']='train'
    with pytest.raises(ValueError,match='differs'):native.verify_native_pair(sample,rgb,labels,expected)


def test_invalid_manifest_is_rejected_before_public_zip_or_image_read(monkeypatch):
    monkeypatch.setattr(native.zipfile,'ZipFile',lambda *a,**k:pytest.fail('Opened unqualified source'))
    with pytest.raises((ValueError,KeyError)):
        native.native_crops(None,None,{},None)


def test_native_pixel_changes_cannot_hide_in_an_unchanged_two_pixel_mean():
    sample,rgb,labels=pair()
    sample.rgb[0,0,0]+=1;sample.rgb[0,1,0]-=1
    assert np.array_equal(training_arrays(sample.rgb,sample.instances)[0],rgb)
    with pytest.raises(ValueError,match='differs'):
        native.verify_native_pair(sample,rgb,labels,sample.record['record_sha256'])
