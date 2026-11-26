"""Bounded native RGB/instance crops from already verified public COCO data.

No trainer, network, customer source discovery or physical-ID interpretation.
One deterministic crop per image is an adapter audit, not full image coverage.
"""
from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
import json
from math import floor

import cv2
import numpy as np
import PIL
from PIL import Image, ImageDraw, features
import rasterio

from .orthophoto_pv_modules import _polygons_mask
from .pvis_training_reference import LABEL_POLICY, annotation_contract

CHECK = 'solarcheck-pvis-image-adapter-1'
PROFILE = dict(id='pvis-rgb-unit-native512-instance-ignore-1', size=512,
    rgb='native_rgb_uint8_to_float32_chw_div255', resize=False,
    coordinates='coco_pixel_corners_sample_at_half_pixel',
    rasterizer='existing_gdal_geometry_mask_pixel_centers_all_touched_false',
    source_edge_margin=1, publisher_area_is_not_mask_checksum=True,
    instance_labels='int32_zero_background_positive_instance_minus1_ignore',
    semantic_labels='uint8_background0_pv1_ignore255',
    ignore='padding_unannotated_source_or_crop_boundary_overlap_plus1pixel',
    sampling='one_crop_per_image_first_complete_annotation_else_center',
    label_policy=LABEL_POLICY, test_pixels_allowed=False)
MAX_PIXELS = 25_000_000
MAX_JPEG = 16_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def value_digest(value):
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def runtime():
    return dict(numpy=np.__version__, pillow=PIL.__version__,
        jpeg=features.version('jpg'), opencv=cv2.__version__,
        rasterio=rasterio.__version__, gdal=rasterio.__gdal_version__, zlib=features.version('zlib'))


def _cancel(callback):
    if callback():
        raise KeyboardInterrupt


def _polygons(annotation):
    return [list(zip(p[::2], p[1::2])) for p in annotation['segmentation']]


def _bounds(annotation):
    points = [p for ring in _polygons(annotation) for p in ring]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def _source_boundary(bounds, width, height):
    x1, y1, x2, y2 = bounds
    # Published projections may already be clipped at the last integer pixel.
    # Require one source pixel of context instead of claiming those are whole.
    return x1 <= 1 or y1 <= 1 or x2 >= width-1 or y2 >= height-1


def crop_window(image, annotations, size=512):
    width, height = image['width'], image['height']
    center = (width / 2, height / 2)
    for annotation in sorted(annotations, key=lambda a: a['id']):
        x1, y1, x2, y2 = _bounds(annotation)
        if not _source_boundary((x1, y1, x2, y2), width, height) and max(x2-x1, y2-y1) <= size-16:
            center = ((x1+x2)/2, (y1+y2)/2)
            break
    return (max(0, min(floor(center[0]-size/2), max(0, width-size))),
            max(0, min(floor(center[1]-size/2), max(0, height-size))), size, size)


@dataclass
class PvisSample:
    rgb: np.ndarray = field(repr=False)
    instances: np.ndarray = field(repr=False)
    semantic: np.ndarray = field(repr=False)
    record: dict

    def model_rgb(self):
        """Explicit RGB CHW unit values; no original CVUT profile claim."""
        return self.rgb.transpose(2, 0, 1).astype(np.float32) / np.float32(255)

    def instance_masks(self):
        """Low-level masks; ignored zeros MUST be paired with valid_pixels."""
        ids = np.unique(self.instances[self.instances > 0])
        return ids, (np.stack([self.instances == i for i in ids]).astype(np.uint8)
                     if len(ids) else np.zeros((0, *self.instances.shape), dtype=np.uint8))

    def instance_targets(self):
        """A trainer must honor validity, not treat ignored mask zeros as negatives."""
        identities, masks = self.instance_masks()
        return dict(instance_ids=identities, masks=masks, valid_pixels=self.semantic != 255)


def load_sample(jpeg, image, annotations, *, station, split, size=512,
                window=None, should_cancel=lambda: False):
    """Caller must first verify the public archive and COCO associations.

    Test pixels are deliberately unavailable through this preparation API.
    Complete projected polygons retain upstream semantics, including occlusion.
    """
    annotation_contract()
    if (station, split) not in {('009', 'train'), ('033', 'validation')}:
        raise PermissionError('Only public training/validation pixels may enter preparation')
    if type(size) is not int or not 16 <= size <= 512:
        raise ValueError('Bounded square crop required')
    width, height = image['width'], image['height']
    if width * height > MAX_PIXELS or not 0 < len(jpeg) <= MAX_JPEG:
        raise ValueError('Public JPEG exceeds bounded decoding limits')
    _cancel(should_cancel)
    with Image.open(BytesIO(jpeg)) as source:
        if source.format != 'JPEG' or source.mode != 'RGB' or source.size != (width, height):
            raise ValueError('JPEG RGB dimensions differ from COCO')
        source.load()  # Decode every source pixel, not merely the JPEG header.
        window = crop_window(image, annotations, size) if window is None else tuple(window)
        if (len(window) != 4 or any(type(v) is not int for v in window)
                or window[2:] != (size, size)
                or not 0 <= window[0] < width or not 0 <= window[1] < height):
            raise ValueError('Native integer crop window outside image')
        left, top, _, _ = window
        rgb = np.array(source.crop((left, top, left+size, top+size)), dtype=np.uint8)
    _cancel(should_cancel)
    instances = np.zeros((size, size), dtype=np.int32)
    ignored = np.zeros((size, size), dtype=bool)
    ignored[max(0, height-top):, :] = True
    ignored[:, max(0, width-left):] = True
    boundary, empty, source_ids = 0, 0, {}
    if not annotations:
        ignored[:] = True  # No claim that an unannotated image is PV-free.
    for ordinal, annotation in enumerate(sorted(annotations, key=lambda a: a['id']), 1):
        _cancel(should_cancel)
        x1, y1, x2, y2 = bounds = _bounds(annotation)
        if x2 <= left or y2 <= top or x1 >= left+size or y1 >= top+size:
            continue
        # Existing helper uses center indices. +0.5 explicitly adapts COCO's
        # corner coordinates to the SAME GDAL pixel-center sampling rule.
        mask = _polygons_mask(_polygons(annotation), width=size, height=size,
                              left=left+.5, top=top+.5)
        if not np.any(mask):
            empty += 1
            continue
        if (_source_boundary(bounds, width, height) or x1 < left or y1 < top
                or x2 > left+size or y2 > top+size):
            ignored |= mask
            boundary += 1
            continue
        ignored |= mask & (instances > 0)
        instances[mask & (instances == 0)] = ordinal
        source_ids[str(ordinal)] = annotation['id']
    ignored = cv2.dilate(ignored.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    instances[ignored] = -1
    semantic = np.where(instances < 0, 255, instances > 0).astype(np.uint8)
    retained = sorted(int(i) for i in np.unique(instances) if i > 0)
    counts = dict(background=int(np.sum(semantic == 0)), pv=int(np.sum(semantic == 1)),
                  ignored=int(np.sum(semantic == 255)))
    record = dict(station=station, split=split, image_id=image['id'], window=list(window),
        jpeg_sha256=sha256(jpeg).hexdigest(),
        rgb_sha256=sha256(rgb.tobytes()).hexdigest(),
        instances_sha256=sha256(instances.astype('<i4').tobytes()).hexdigest(),
        semantic_sha256=sha256(semantic.tobytes()).hexdigest(), pixels=counts,
        retained_instances=len(retained), boundary_instances_ignored=boundary,
        empty_instance_masks=empty, unannotated_image=not bool(annotations),
        source_annotation_ids={str(i): source_ids[str(i)] for i in retained},
        eligible=bool(retained and counts['background'] and counts['pv']))
    record['record_sha256'] = value_digest(record)
    return PvisSample(rgb, instances, semantic, record)


def preview(sample):
    """New metadata-free diagnostic sheet; public RGB, instances and overlay."""
    ids = sample.instances
    palette = np.array([[0, 220, 120], [255, 190, 0], [0, 170, 255], [255, 80, 100],
                        [170, 140, 255], [120, 230, 40]], dtype=np.uint8)
    colored = np.zeros_like(sample.rgb)
    positive = ids > 0
    colored[positive] = palette[(ids[positive]-1) % len(palette)]
    colored[ids < 0] = (255, 0, 255)
    overlay = sample.rgb.copy()
    marked = ids != 0
    overlay[marked] = (sample.rgb[marked].astype(np.float32)*.5 + colored[marked]*.5).astype(np.uint8)
    size = ids.shape[0]
    sheet = Image.new('RGB', (3*size, size+24), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, (pixels, label) in enumerate(zip((sample.rgb, colored, overlay),
            ('RGB native', 'Instanzen: Magenta ignoriert', 'Ueberlagerung'))):
        sheet.paste(Image.fromarray(pixels), (index*size, 24))
        draw.text((index*size+4, 4), label, fill='black')
    return sheet
