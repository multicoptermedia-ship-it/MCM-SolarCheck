"""Public033 full-image development comparison, separate from old crop metrics.

Only inference sees RGB tiles; COCO labels enter the evaluator afterwards.
The three hard development images are not an independent accuracy test.
"""
from contextlib import redirect_stdout
from hashlib import sha256
from io import BytesIO, StringIO
import json
import zipfile

import cv2
import numpy as np

from .pvis_public_training_data import fingerprint
from ..vision import cvut_yolo_validation as inference
from ..vision.cvut_yolo_outlines import projective_outlines
from ..vision.detection import ModuleDetection
from ..vision.module_quality import filter_module_detections
from ..vision.module_tiles import detect_tiles

CHECK = 'solarcheck-cvut-yolo-full-image-tiling-1'
CASES = (14, 17, 18)
PROFILES = (('grid512_iou', (512,), 'iou'),
            ('grid1024_iou', (1024,), 'iou'),
            ('multiscale_iou', (1024, 512), 'iou'),
            ('multiscale_ios', (1024, 512), 'ios'))
METHODS = ('whole_image256',) + tuple(p[0] for p in PROFILES)
COUNTS = ('reference_instances', 'predictions', 'matched_instances',
          'additional_predictions', 'missed_references')
PROFILE = dict(id='public033-fixed-full-image-development-1', cases=CASES,
    evaluation='pycocotools2.0.10_mask_iou050_and075_maxdet5000',
    whole_image='native_square_bottom_right_padding_area256',
    reference='projected_whole_module_coco_pixel_corners',
    reference_labels_used_for_inference=False, independent_test=False)


def score_coco(image, categories, annotations, detections):
    """Official COCO mask matching; integer ignore arrays are not bitwise masks."""
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    from pycocotools import mask as masks
    if len(detections) > 5000 or len(categories) != 1:
        raise ValueError('Bounded single-category public evaluation required')
    predictions = []
    for detection in detections:
        corners = [float(v + .5) for point in detection.polygon_px for v in point]
        rle = masks.merge(masks.frPyObjects([corners], image['height'], image['width']))
        predictions.append(dict(image_id=image['id'], category_id=categories[0]['id'],
            score=detection.confidence, segmentation=rle))
    with redirect_stdout(StringIO()):
        gt = COCO()
        gt.dataset = dict(info={}, images=[image], categories=categories, annotations=annotations)
        gt.createIndex()
        if predictions:
            dt = gt.loadRes(predictions)
        else:
            dt = COCO()
            dt.dataset = dict(images=[image], categories=categories, annotations=[])
            dt.createIndex()
        evaluator = COCOeval(gt, dt, 'segm')
        evaluator.params.imgIds = [image['id']]
        evaluator.params.iouThrs = np.array([.5, .75])
        evaluator.params.maxDets = [1, 100, 5000]
        evaluator.evaluate()
        evaluator.accumulate()
    item = next(x for x in evaluator.evalImgs if x is not None
                and x['aRng'] == evaluator.params.areaRng[0])
    result = {}
    for index, name in enumerate(('iou050', 'iou075')):
        matches, ignored = item['dtMatches'][index], item['dtIgnore'][index].astype(bool)
        matched = int(((matches > 0) & ~ignored).sum())
        extra = int(((matches == 0) & ~ignored).sum())
        count = int((item['gtIgnore'] == 0).sum())
        precision = evaluator.eval['precision'][index, :, 0, 0, -1]
        ap = float(precision[precision >= 0].mean()) if np.any(precision >= 0) else None
        result[name] = dict(reference_instances=count, predictions=len(predictions),
            matched_instances=matched, additional_predictions=extra,
            missed_references=count-matched, AP=ap)
    return result


def compare_image(rgb, detector, *, should_cancel=lambda: False, progress=lambda n, total: None):
    """No annotations/counts/ignore labels are arguments to this inference path."""
    height, width = rgb.shape[:2]
    cache = {}
    def cached(pixels):
        if should_cancel():
            raise KeyboardInterrupt
        key = sha256(pixels.tobytes()).digest()
        if key not in cache:
            cache[key] = detector(pixels)
        return cache[key]
    side = max(width, height)
    square = np.zeros((side, side, 3), np.uint8)
    square[:height, :width] = rgb
    small = cv2.resize(square, (256, 256), interpolation=cv2.INTER_AREA)
    del square
    scale = side/256
    mapped = tuple(ModuleDetection(tuple(((x+.5)*scale-.5, (y+.5)*scale-.5)
        for x, y in d.polygon_px), d.confidence, d.class_name) for d in cached(small))
    whole = filter_module_detections(mapped, width, height, duplicate_iou=.5,
        minimum_area_fraction=16/(width*height), maximum_area_fraction=1.)
    detections, diagnostics = dict(whole_image256=whole), {}
    for name, sizes, metric in PROFILES:
        detections[name], diagnostics[name] = detect_tiles(rgb, cached, sizes=sizes,
            duplicate_metric=metric, should_cancel=should_cancel, progress=progress)
    return detections, diagnostics, len(cache)


def compare(torch, model, source, manifest, audit, *, should_cancel=lambda: False,
            progress=lambda n, total: None):
    """Only the previously selected three whole033 images, publisher SHA first."""
    from PIL import Image
    source = source/audit.VALIDATION.name
    if should_cancel():
        raise KeyboardInterrupt
    audit.inspect_station(source, audit.VALIDATION)
    selected = {r['sample_id']: i+1 for i, r in enumerate(
        [row for row in manifest['samples'] if row['split'] == 'validation'])}
    rows = []
    with zipfile.ZipFile(source) as archive:
        coco = json.loads(archive.read(audit.VALIDATION.prefix+'instances.json'))
        images = [(selected[fingerprint(dict(station='033', image_id=image['id']))], image)
            for image in coco['images']
            if selected.get(fingerprint(dict(station='033', image_id=image['id']))) in CASES]
        if sorted(case for case, _ in images) != list(CASES):
            raise ValueError('Fixed public033 development images differ')
        for case, image in sorted(images):
            if should_cancel():
                raise KeyboardInterrupt
            width, height = image['width'], image['height']
            if (width, height) != (5280, 3956):
                raise ValueError('Expected verified public033 native image dimensions')
            name = image['file_name']
            if not name.startswith('images/'):
                name = 'images/'+name
            if '..' in name.split('/') or '\\' in name:
                raise ValueError('Unexpected public image member')
            with Image.open(BytesIO(archive.read(audit.VALIDATION.prefix+name))) as photo:
                if photo.mode != 'RGB' or photo.size != (width, height):
                    raise ValueError('Native public RGB differs')
                rgb = np.array(photo)
            def detector(pixels):
                boxes, masks, confidence = inference.infer(torch, model, pixels)
                return projective_outlines(boxes, masks, confidence)[1]
            detections, diagnostics, computed = compare_image(rgb, detector,
                should_cancel=should_cancel, progress=progress)
            annotations = [a for a in coco['annotations'] if a['image_id'] == image['id']]
            metrics = {}
            for method in METHODS:
                if should_cancel():
                    raise KeyboardInterrupt
                metrics[method] = score_coco(image, coco['categories'], annotations, detections[method])
            rows.append(dict(public_case=case, width=width, height=height, metrics=metrics,
                tile_diagnostics=diagnostics, model_windows_computed=computed))
    return dict(check=CHECK, profile=PROFILE, images=rows,
        totals={method: {threshold: {key: sum(r['metrics'][method][threshold][key] for r in rows)
            for key in COUNTS} for threshold in ('iou050', 'iou075')} for method in METHODS})


def verify_report(value):
    """Reopen without COCO, Torch, JPEG decoding or inference."""
    rows = value.get('images')
    if (value.get('profile') != json.loads(json.dumps(PROFILE)) or not isinstance(rows, list)
            or [r.get('public_case') for r in rows] != list(CASES)):
        raise ValueError('Fixed full-image comparison identity differs')
    for row in rows:
        if (row.get('width'), row.get('height')) != (5280, 3956):
            raise ValueError('Native public image dimensions differ')
        if set(row.get('metrics', {})) != set(METHODS):
            raise ValueError('Full-image comparison methods differ')
        for method in METHODS:
            for threshold in ('iou050', 'iou075'):
                counts = row['metrics'][method][threshold]
                if (any(type(counts.get(k)) is not int or not 0 <= counts[k] <= 5000 for k in COUNTS)
                        or counts['matched_instances']+counts['missed_references'] != counts['reference_instances']
                        or counts['matched_instances']+counts['additional_predictions'] != counts['predictions']
                        or counts.get('AP') is not None and (not isinstance(counts['AP'], (int, float))
                            or not 0 <= counts['AP'] <= 1)):
                    raise ValueError('Full-image counts differ or were truncated')
    expected = {method: {threshold: {k: sum(r['metrics'][method][threshold][k] for r in rows)
        for k in COUNTS} for threshold in ('iou050', 'iou075')} for method in METHODS}
    if value.get('totals') != expected:
        raise ValueError('Full-image totals differ')
    return value
