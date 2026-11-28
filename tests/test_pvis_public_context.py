"""Synthetic public-source, pixel-policy and verified-subset contracts."""
from hashlib import sha256
from io import BytesIO
import json
import zipfile

import numpy as np
from PIL import Image
import pytest

from mcm_solarcheck.services import pvis_public_context as context
from mcm_solarcheck.services import pvis_public_extra_sites as extra
from mcm_solarcheck.services.pvis_public_training_data import training_arrays


def annotation(identity, box, image_id=1):
    x, y, w, h = box
    return dict(id=identity, image_id=image_id, category_id=1, bbox=list(box),
        area=w*h, segmentation=[[x,y,x+w,y,x+w,y+h,x,y+h]], iscrowd=0)


def jpeg():
    rgb = np.full((1024, 1024, 3), 180, np.uint8)
    rgb[250:400, 250:500] = (30, 70, 110)
    stream = BytesIO()
    Image.fromarray(rgb).save(stream, format='JPEG')
    return stream.getvalue()


@pytest.mark.parametrize('site', ['018', '029'])
def test_new_site_preserves_original_whole_polygon_and_unknown_pixel_policy(site):
    image = dict(id=1, width=1024, height=1024)
    anns = [annotation(1, (260,260,180,100)), annotation(2,(90,300,80,40)),
            annotation(3,(380,300,130,100))]
    data = jpeg()
    window = (128,128,512,512)
    original = context.original.load_sample(data, image, anns, station='009',
        split='train', window=window)
    expected_rgb, expected_labels = training_arrays(original.rgb, original.instances)
    rgb, labels, record = context.training_sample(data, image, anns, station=site, window=window)
    assert np.array_equal(rgb, expected_rgb)
    assert np.array_equal(labels, expected_labels)
    assert set(np.unique(labels)) == {-1, 0, 1, 3}
    assert record['station'] == site and record['split'] == 'train'
    assert record['jpeg_sha256'] == sha256(data).hexdigest()


@pytest.mark.parametrize('site', ['024', '033', 'customer', '999'])
def test_training_sites_cannot_alias_reserved_or_private_inputs(site, monkeypatch):
    monkeypatch.setattr(context.Image, 'open', lambda *a, **k: pytest.fail('Decoded forbidden input'))
    with pytest.raises(PermissionError):
        context.training_sample(b'not-read', {}, [], station=site, window=(0,0,512,512))


def test_context_selection_is_deterministic_and_spatially_separated():
    image = dict(width=2048, height=2048)
    anns = [annotation(i, b) for i,b in enumerate(((100,100,160,80),
        (1700,100,160,80),(100,1700,160,80),(1700,1700,160,80)), 1)]
    windows = context.context_windows(image, anns)
    assert windows == context.context_windows(image, anns[::-1])
    assert len(windows) == 4
    assert all((a[0]-b[0])**2+(a[1]-b[1])**2 >= 512**2
               for i,a in enumerate(windows) for b in windows[i+1:])


@pytest.mark.parametrize('limit', [0, 5, True, '4'])
def test_unbounded_context_requests_are_rejected(limit):
    with pytest.raises(ValueError):
        context.context_windows(dict(width=1024,height=1024), [], maximum=limit)


def public_zip(monkeypatch, *, count=1, mutate=lambda c: None, extra_member=None):
    images = [dict(id=i,width=1024,height=1024,file_name=f'{i}.jpg') for i in range(count)]
    anns = [annotation(i,(200,200,160,80),i) for i in range(count)]
    coco = dict(images=images, annotations=anns, categories=[dict(id=1,name='pv_panel')])
    mutate(coco)
    payload = json.dumps(coco).encode()
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('train/018/instances.json', payload)
        for image in images:
            archive.writestr('train/018/images/'+image['file_name'], b'synthetic-not-decoded')
        if extra_member is not None:
            archive.writestr(extra_member, b'not-read')
    raw = buffer.getvalue()
    unpacked = len(payload)+count*len(b'synthetic-not-decoded')
    spec = extra.PublicSite('018',count,count,unpacked,len(raw),sha256(raw).hexdigest())
    monkeypatch.setitem(extra.SITES,'018',spec)
    return BytesIO(raw), spec


def test_publisher_identity_precedes_metadata_and_no_image_is_decoded(monkeypatch):
    buffer, spec = public_zip(monkeypatch)
    monkeypatch.setattr(context.Image,'open',lambda *a,**k:pytest.fail('Inventory decoded JPEG'))
    archive, coco = extra.verified_zip(buffer,'018')
    assert len(coco['images']) == 1
    assert archive._solarcheck_verified_public_source == ('018',spec.size,spec.sha256)
    archive.close()
    corrupted = BytesIO(buffer.getvalue()+b'changed')
    with pytest.raises(ValueError,match='checksum'):
        extra.verified_zip(corrupted,'018')


@pytest.mark.parametrize('member', ['../escape','/escape','train/029/images/wrong.jpg',
    'train/018/model.pt','train\\018\\bad.jpg'])
def test_verified_bytes_do_not_bypass_public_archive_scope(monkeypatch,member):
    buffer,_ = public_zip(monkeypatch,extra_member=member)
    with pytest.raises(ValueError):
        extra.verified_zip(buffer,'018')


@pytest.mark.parametrize('mutation', [
    lambda c:c['categories'][0].update(name='roof'),
    lambda c:c['annotations'][0].update(image_id=999),
    lambda c:c['annotations'][0].update(category_id=True),
    lambda c:c['annotations'][0].update(bbox=[0,0,9999,20]),
    lambda c:c['annotations'][0].update(segmentation=[[0,0,20,0,float('nan'),20]]),
])
def test_changed_coco_semantics_and_associations_are_rejected(monkeypatch,mutation):
    buffer,_ = public_zip(monkeypatch,mutate=mutation)
    with pytest.raises(ValueError):
        extra.verified_zip(buffer,'018')


def cached_subset(tmp_path,monkeypatch):
    buffer,_ = public_zip(monkeypatch,count=20)
    archive,_ = extra.verified_zip(buffer,'018')
    samples=[]
    for i in range(20):
        rgb=np.zeros((256,256,3),np.uint8)
        labels=np.zeros((256,256),np.int32)
        labels[32:96,32:96]=1
        labels[:4]=-1
        record=dict(station='018',split='train',image_id=i,window=[0,0,512,512],
            retained_instances=1,jpeg_sha256='a'*64)
        samples.append((rgb,labels,record))
    extra.write_context_cache(tmp_path,'018',samples,verified_archive=archive)
    archive.close()
    return samples


def test_verified_numeric_subset_reopens_without_source_zip_or_torch(tmp_path,monkeypatch):
    samples=cached_subset(tmp_path,monkeypatch)
    reopened=extra.read_context_cache(tmp_path,'018')
    assert len(reopened)==20
    for (a,b,r),(x,y,s) in zip(samples,reopened):
        assert np.array_equal(a,x) and np.array_equal(b,y) and r==s
    with pytest.raises(ValueError,match='Preserve'):
        buffer,_=public_zip(monkeypatch,count=20)
        archive,_=extra.verified_zip(buffer,'018')
        try:extra.write_context_cache(tmp_path,'018',samples,verified_archive=archive)
        finally:archive.close()


@pytest.mark.parametrize('field,value', [('station','033'),('split','test'),
    ('customer_images',1),('test_images',1),('commercial_training_approved',True)])
def test_resealed_cache_cannot_change_training_scope(tmp_path,monkeypatch,field,value):
    cached_subset(tmp_path,monkeypatch)
    p=tmp_path/'018/contexts.json'
    data=json.loads(p.read_text());data[field]=value
    p.write_text(json.dumps(extra._seal(data)))
    with pytest.raises((ValueError,PermissionError)):
        extra.read_context_cache(tmp_path,'018')


def test_cache_member_escape_is_rejected_before_read(tmp_path,monkeypatch):
    cached_subset(tmp_path,monkeypatch)
    p=tmp_path/'018/contexts.json';data=json.loads(p.read_text())
    data['samples'][0]['sample_id']='../private'
    p.write_text(json.dumps(extra._seal(data)))
    monkeypatch.setattr(extra.numeric,'read_crop',lambda *a,**k:pytest.fail('Read escaped member'))
    with pytest.raises(ValueError):extra.read_context_cache(tmp_path,'018')


def test_unverified_archive_cannot_publish_numeric_subset(tmp_path):
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w'):pass
    with zipfile.ZipFile(stream) as archive:
        with pytest.raises(ValueError,match='completely verified'):
            extra.write_context_cache(tmp_path,'018',[],verified_archive=archive)


def test_incomplete_subset_never_publishes_active_manifest(tmp_path,monkeypatch):
    buffer,_ = public_zip(monkeypatch,count=20)
    archive,_ = extra.verified_zip(buffer,'018')
    try:
        with pytest.raises(ValueError,match='20-image'):
            extra.write_context_cache(tmp_path,'018',[],verified_archive=archive)
    finally:
        archive.close()
    assert not (tmp_path/'018/contexts.json').exists()
