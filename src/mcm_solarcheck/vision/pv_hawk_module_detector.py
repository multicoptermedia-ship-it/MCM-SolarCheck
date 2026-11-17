"""Approved isolated PV-Hawk RGB evaluation. No network, training or approval.

The original model implementation and published weights are hash pinned. Only
its inference graph is built, never an H5-serialized architecture or Lambda.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys
import types

import cv2
import numpy as np

from .detection import ModuleDetection

PROFILE = 'pv-hawk-rgb-cpu-evaluation-1'
SPEC_PATH = Path(__file__).resolve().parents[3] / 'config/pv-hawk/rgb-v1.json'


def specification():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8'))


def checked_bytes(path, expected):
    path = Path(path)
    if (not path.is_file() or any(p.is_symlink() for p in (path, *path.parents))
            or path.stat().st_size != expected['bytes']):
        raise ValueError('PV-Hawk-Datei fehlt oder hat ungueltige Groesse.')
    content = path.read_bytes()
    if sha256(content).hexdigest() != expected['sha256']:
        raise ValueError('PV-Hawk-Pruefsumme stimmt nicht.')
    return content


def validate_manifest(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or path.stat().st_size > 32768:
        raise ValueError('Lokale PV-Hawk-Modellbeschreibung erforderlich.')
    data = json.loads(path.read_text(encoding='utf-8'))
    spec = specification()
    if (data.get('profile') != PROFILE or data.get('evaluation_allowed') is not True
            or data.get('production_approved') is not False
            or data.get('source_commit') != spec['source_commit']
            or data.get('weights_sha256') != spec['weights_sha256']):
        raise ValueError('Geprueften getrennten PV-Hawk-Pilot einrichten.')
    return path.parent, data, spec


def evaluation_python(path):
    """Select only the pilot's own sibling environment, no manifest command."""
    root, _, _ = validate_manifest(path)
    executable = root / ('env/Scripts/python.exe' if sys.platform == 'win32' else 'env/bin/python')
    if not executable.is_file():
        raise ValueError('Getrennte PV-Hawk-Umgebung fehlt; Einrichtungsstart ausfuehren.')
    return str(executable)


def _module(name, content, filename):
    # TensorFlow AutoGraph retrieves source again via inspect/linecache. Give
    # it the exact adapted text, rather than the untouched upstream disk file.
    import linecache
    filename = str(filename) + '-solarcheck-cpu-bridge'
    linecache.cache[filename] = (len(content), None, content.splitlines(True), filename)
    module = types.ModuleType(name)
    module.__file__ = filename
    sys.modules[name] = module
    exec(compile(content, str(filename), 'exec'), module.__dict__)
    return module


def _model(root, spec):
    # Hash-check every source before any upstream code executes. Ignore pyc,
    # local import hooks and other files alongside the allowed source subset.
    sources = {name: checked_bytes(root / 'vendor' / name, check)
               for name, check in spec['sources'].items()}
    import tensorflow as tf
    import keras
    if tf.__version__ != '2.10.1' or keras.__version__ != '2.10.0' or sys.version_info[:2] != (3, 10):
        raise RuntimeError('PV-Hawk benoetigt seine getrennte Python-3.10/TF-2.10.1-CPU-Umgebung.')
    tf.config.set_visible_devices([], 'GPU')
    tf.compat.v1.disable_eager_execution()
    package = types.ModuleType('mrcnn')
    package.__path__ = []
    sys.modules['mrcnn'] = package
    prefix = 'extractor/segmentation/Mask_RCNN/mrcnn/'
    for name in ('config', 'utils', 'model'):
        content = sources[prefix+name+'.py'].decode('utf-8')
        # API compatibility only: original architecture/weights/preprocessing.
        content = content.replace('import tensorflow as tf', 'import tensorflow.compat.v1 as tf')
        if name == 'model':
            for before, after in (
                ('import keras.engine as KE', 'import keras.layers as KE'),
                ('KL.Reshape((s[1], num_classes, 4)', 'KL.Reshape((-1, num_classes, 4)'),
                ('tf.range(probs.shape[0])', 'tf.range(tf.shape(probs)[0])'),
            ):
                if content.count(before) != 1:
                    raise RuntimeError('PV-Hawk-Kompatibilitaetsstand passt nicht.')
                content = content.replace(before, after)
        module = _module('mrcnn.'+name, content, root / 'vendor' / (prefix+name+'.py'))
        setattr(package, name, module)
    # Read the exact upstream PVConfig, with its import directed to the checked
    # Config module above. No other extractor/video/SfM imports are executed.
    content = sources['extractor/segmentation/configs.py'].decode('utf-8')
    start, end = content.index('try:'), content.index('\n\n\nclass PVConfig')
    content = content[:start] + 'from mrcnn.config import Config' + content[end:]
    config_class = _module('solarcheck_pv_hawk_config', content, root/'vendor/extractor/segmentation/configs.py').PVConfig
    config_class.IMAGES_PER_GPU = 1
    config = config_class()
    model = package.model.MaskRCNN(mode='inference', config=config, model_dir=str(root/'model-log'))
    # Upstream trains with loss layers, whose order differs from inference.
    # Require every inference layer's full weights, then use upstream's named
    # loading with strict shape checks. Never deserialize an H5 architecture.
    import h5py
    with h5py.File(root/spec['weights'], 'r') as weights:
        for layer in model.keras_model.layers:
            if not layer.weights:
                continue
            if layer.name not in weights:
                raise ValueError('PV-Hawk-Modellschicht fehlt in den RGB-Gewichten.')
            group = weights[layer.name]
            names = group.attrs.get('weight_names', [])
            shapes = [tuple(group[n.decode() if isinstance(n,bytes) else n].shape) for n in names]
            if shapes != [tuple(w.shape) for w in layer.weights]:
                raise ValueError('PV-Hawk-Gewichte passen nicht vollstaendig zum Inferenzmodell.')
    model.keras_model.load_weights(str(root/spec['weights']), by_name=True, skip_mismatch=False)
    return model


def mask_detections(result, shape):
    height, width = shape[:2]
    masks, scores, classes = (np.asarray(result[k]) for k in ('masks','scores','class_ids'))
    if (masks.shape != (height, width, len(scores)) or scores.ndim != 1
            or classes.shape != scores.shape or len(scores) > 200
            or not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1))):
        raise ValueError('Ungueltige PV-Hawk-Instanzmasken.')
    found = []
    for i, score in enumerate(scores):
        if classes[i] != 1 or score < .7:
            continue
        contours, _ = cv2.findContours(masks[:,:,i].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) != 1 or cv2.contourArea(contours[0]) < 4:
            continue
        polygon = cv2.boxPoints(cv2.minAreaRect(contours[0]))
        if any(x < 0 or y < 0 or x > width-1 or y > height-1 for x,y in polygon):
            continue
        found.append(ModuleDetection(tuple((float(x),float(y)) for x,y in polygon),float(score)))
    return tuple(found)


class PVHawkModuleDetector:
    def __init__(self, path):
        self.root, data, self.spec = validate_manifest(path)
        self._check_weights()
        self.model = _model(self.root, self.spec)
        self.name = 'pv-hawk-rgb-v1-cpu-evaluation'
        self.description = dict(provider='LukasBommes/PV-Hawk', model_version='v1.0.0-rgb-0059',
            profile=PROFILE, source_commit=self.spec['source_commit'],
            weights_sha256=self.spec['weights_sha256'], code_license='MIT',
            weight_rights='Published project release; separate weight/data terms not independently cleared for production/distribution.',
            backend='tensorflow-cpu-2.10.1', preprocessing='upstream-PVConfig-RGB-512-640-mean129.4',
            evaluation_allowed=True, production_approved=False)

    def _check_weights(self):
        checked_bytes(self.root / self.spec['weights'],
            dict(bytes=self.spec['weights_bytes'],sha256=self.spec['weights_sha256']))

    def detect_array(self, image):
        if (image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3
                or not 1 <= min(image.shape[:2]) or max(image.shape[:2]) > 2048):
            raise ValueError('Begrenzter uint8-RGB-Ausschnitt erforderlich.')
        result = self.model.detect([np.ascontiguousarray(image[:,:,::-1])], verbose=0)[0]
        self._check_weights()
        return mask_detections(result,image.shape)
