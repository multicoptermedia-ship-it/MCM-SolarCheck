"""Versioned public-only sampling for additional training sites.

The original native512 adapter is source-bound to already saved runs. Keep it
unchanged and reuse its rasterizer/geometry policy for the two new sites.
"""
from hashlib import sha256
from io import BytesIO
import json

import cv2
import numpy as np
from PIL import Image

from . import pvis_image_adapter as original
from .pvis_public_training_data import training_arrays

TRAIN_SITES = frozenset(('009', '018', '029'))


def context_windows(image, annotations, *, maximum=4):
    """Fixed first window, then farthest complete-annotation centers."""
    if type(maximum) is not int or not 1 <= maximum <= 4:
        raise ValueError('At most four public contexts per image')
    width, height = image['width'], image['height']
    if min(width, height) < 512:
        raise ValueError('Native512 source context required')
    windows = [original.crop_window(image, annotations, 512)]
    choices = set()
    for annotation in annotations:
        x1, y1, x2, y2 = bounds = original._bounds(annotation)
        if original._source_boundary(bounds, width, height) or max(x2-x1, y2-y1) > 496:
            continue
        left = max(0, min(int((x1+x2)/2-256), width-512))
        top = max(0, min(int((y1+y2)/2-256), height-512))
        choices.add((left, top, 512, 512))
    def distance(window):
        return min((window[0]-v[0])**2+(window[1]-v[1])**2 for v in windows)
    while len(windows) < maximum and choices:
        window = min(choices, key=lambda w: (-distance(w), w))
        if distance(window) < 512**2:
            break
        windows.append(window)
        choices.remove(window)
    return tuple(windows)


def training_sample(jpeg, image, annotations, *, station, window):
    """Only declared public training sites; never a test/validation alias.

    Complete projected module polygons remain complete targets. Source/crop
    boundary instances and overlaps retain the original ignore policy.
    """
    if station not in TRAIN_SITES:
        raise PermissionError('Declared public training sites only')
    if station == '009':
        sample = original.load_sample(jpeg, image, annotations, station=station,
            split='train', window=window)
        pixels, labels = training_arrays(sample.rgb, sample.instances)
        return pixels, labels, sample.record
    original.annotation_contract()
    width, height = image['width'], image['height']
    if (width*height > original.MAX_PIXELS or not 0 < len(jpeg) <= original.MAX_JPEG
            or type(window) is not tuple or len(window) != 4
            or any(type(v) is not int for v in window) or window[2:] != (512, 512)
            or not 0 <= window[0] <= width-512 or not 0 <= window[1] <= height-512):
        raise ValueError('Bounded native public RGB context required')
    left, top, _, _ = window
    with Image.open(BytesIO(jpeg)) as source:
        if source.format != 'JPEG' or source.mode != 'RGB' or source.size != (width, height):
            raise ValueError('Public JPEG and COCO dimensions differ')
        source.load()
        rgb = np.array(source.crop((left, top, left+512, top+512)), dtype=np.uint8)
    labels = np.zeros((512, 512), np.int32)
    ignored = np.zeros((512, 512), bool)
    if not annotations:
        ignored[:] = True
    for ordinal, annotation in enumerate(sorted(annotations, key=lambda a: a['id']), 1):
        x1, y1, x2, y2 = bounds = original._bounds(annotation)
        if x2 <= left or y2 <= top or x1 >= left+512 or y1 >= top+512:
            continue
        mask = original._polygons_mask(original._polygons(annotation), width=512,
            height=512, left=left+.5, top=top+.5)
        if (original._source_boundary(bounds, width, height) or x1 < left or y1 < top
                or x2 > left+512 or y2 > top+512):
            ignored |= mask
            continue
        ignored |= mask & (labels > 0)
        labels[mask & (labels == 0)] = ordinal
    ignored = cv2.dilate(ignored.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    labels[ignored] = -1
    pixels, targets = training_arrays(rgb, labels)
    record = dict(station=station, split='train', image_id=image['id'], window=list(window),
        jpeg_sha256=sha256(jpeg).hexdigest(), rgb_sha256=sha256(rgb.tobytes()).hexdigest(),
        instances_sha256=sha256(labels.astype('<i4').tobytes()).hexdigest(),
        retained_instances=len(np.unique(targets[targets > 0])))
    record['record_sha256'] = sha256(json.dumps(record, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    return pixels, targets, record
