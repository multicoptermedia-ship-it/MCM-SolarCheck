"""Public numeric research augmentation: complete objects, unknown remains unknown.

No file/network/model access. The caller must admit only verified public crops.
Small objects without a supported anchor must not be taught as background.
"""
import cv2
import numpy as np

PROFILE = dict(id='pvis-small-object-zoom-anchor-support-2',size=256,
    zoom_windows=(64,128,192),zoom_on_even_steps=True,
    partial_instances='entire_visible_fragment_ignored_plus1pixel',
    resized_unknown='bilinear_valid_support_must_be_exactly_one',
    unsupported_instances='whole_instance_ignored_until_anchor_support_stable',
    strides=(8,16,32),anchor_validity='all_source_pixels_in_stride_cell_known',
    only_shorter_than8_or_unsupported_objects=True,maximum_origin_shift=3,
    photometric_changes=False,source_pixels_modified=False)


def supported_instances(target):
    """Match the reference assigner's strict inside-box center convention."""
    valid=target>=0
    grids=[]
    for stride in (8,16,32):
        known=valid.reshape(256//stride,stride,256//stride,stride).all((1,3))
        y,x=np.meshgrid(np.arange(stride//2,256,stride),
            np.arange(stride//2,256,stride),indexing='ij')
        grids.append((x,y,known))
    result=[]
    for identity in np.unique(target[target>0]):
        y,x=np.nonzero(target==identity)
        if any(np.any((gx>x.min())&(gx<x.max()+1)&(gy>y.min())&(gy<y.max()+1)&known)
               for gx,gy,known in grids):
            result.append(int(identity))
    return tuple(result)


def prepare(rgb,target,step,*,force_zoom=False):
    if (not isinstance(rgb,np.ndarray) or rgb.dtype!=np.uint8 or rgb.shape!=(256,256,3)
            or not isinstance(target,np.ndarray) or target.dtype!=np.int32
            or target.shape!=(256,256) or target.min() < -1 or target.max()>10000
            or type(step) is not int or step<0 or type(force_zoom) is not bool):
        raise ValueError('Bounded public numeric crop and deterministic nonnegative step required')
    image,labels=rgb.copy(),target.copy()
    ids=np.unique(target[target>0]);unsupported=set(map(int,ids))-set(supported_instances(target))
    choices=[]
    for identity in ids:
        y,x=np.nonzero(target==identity)
        windows=[n for n in (64,128,192) if max(x.max()+1-x.min(),y.max()+1-y.min())+8<=n]
        if windows and (int(identity) in unsupported or min(x.max()+1-x.min(),y.max()+1-y.min())<8):
            choices.append((int(identity),windows[0],int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)))
    zoomed=False;partial=0
    if (step%2==0 or force_zoom) and choices:
        preferred=[c for c in choices if c[0] in unsupported] or choices
        identity,size,x1,y1,x2,y2=preferred[(step//2)%len(preferred)]
        left=max(0,min((x1+x2-size)//2,256-size));top=max(0,min((y1+y2-size)//2,256-size))
        offsets=sorted(((dx,dy) for dx in range(-3,4) for dy in range(-3,4)),
            key=lambda p:(abs(p[0])+abs(p[1]),p[1],p[0]))
        for dx,dy in offsets:
            x=max(0,min(left+dx,256-size));y=max(0,min(top+dy,256-size))
            cropped=target[y:y+size,x:x+size].copy();cut=np.zeros_like(cropped,bool);removed=0
            for other in np.unique(cropped[cropped>0]):
                if np.sum(cropped==other)!=np.sum(target==other):
                    cut|=cropped==other;removed+=1
            cropped[cv2.dilate(cut.astype(np.uint8),np.ones((3,3),np.uint8))>0]=-1
            candidate=cv2.resize(cropped,(256,256),interpolation=cv2.INTER_NEAREST).astype(np.int32)
            known=cv2.resize((cropped>=0).astype(np.float32),(256,256),interpolation=cv2.INTER_LINEAR)==1
            candidate[~known]=-1
            if identity in supported_instances(candidate) and np.any(candidate==0):
                image=cv2.resize(rgb[y:y+size,x:x+size],(256,256),interpolation=cv2.INTER_LINEAR)
                labels=candidate;zoomed=True;partial=removed
                break
    ignored=set()
    for _ in range(len(np.unique(labels[labels>0]))+1):
        unsupported=set(map(int,np.unique(labels[labels>0])))-set(supported_instances(labels))
        if not unsupported:
            break
        remove=np.isin(labels,list(unsupported));ignored.update(unsupported)
        labels[cv2.dilate(remove.astype(np.uint8),np.ones((3,3),np.uint8))>0]=-1
    retained=len(np.unique(labels[labels>0]))
    return image,labels,dict(zoomed=zoomed,partial_instances_ignored=partial if zoomed else 0,
        unsupported_instances_ignored=len(ignored),retained_instances=retained,
        eligible=bool(retained and np.any(labels==0)))
