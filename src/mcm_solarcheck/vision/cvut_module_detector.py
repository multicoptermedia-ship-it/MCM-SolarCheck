"""Explicit isolated CVUT candidate; no network, training or production approval.

The external reference source is GPL-3.0 and remains in the private pilot
folder with its license. This is no licensing decision for product packaging.
Input processing/class mapping are a candidate profile, not verified CVUT code.
"""
from collections import OrderedDict
from io import BytesIO
import json
from pathlib import Path
import sys
import types

import cv2
import numpy as np

from .detection import ModuleDetection
from .pv_hawk_module_detector import checked_bytes

PROFILE = 'cvut-unet-rgb-cpu-candidate-1'
SPEC_PATH = Path(__file__).resolve().parents[3] / 'config/cvut/rgb-candidate-v1.json'


def specification():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8'))


def validate_manifest(path):
    path = Path(path)
    if (not path.is_absolute() or not path.is_file() or path.stat().st_size > 32768
            or any(p.is_symlink() for p in (path, *path.parents))):
        raise ValueError('Lokale CVUT-Kandidatenbeschreibung ausserhalb von Verknuepfungen erforderlich.')
    data, spec = json.loads(path.read_text(encoding='utf-8')), specification()
    if (not isinstance(data, dict) or data.get('profile') != PROFILE
            or data.get('evaluation_allowed') is not True or data.get('production_approved') is not False
            or data.get('source_commit') != spec['source_commit']
            or data.get('weights_sha256') != spec['weights_sha256']):
        raise ValueError('Geprueften eigenen CVUT-CPU-Pilot einrichten.')
    return path.parent, data, spec


def evaluation_python(path):
    root, _, _ = validate_manifest(path)
    executable = root / ('env/Scripts/python.exe' if sys.platform == 'win32' else 'env/bin/python')
    if not executable.is_file() or any(p.is_symlink() for p in executable.parents):
        raise ValueError('Eigene CVUT-CPU-Umgebung fehlt.')
    return str(executable)


def reference_model(root, spec, torch):
    # Check ALL sources before executing the small selected reference subset.
    # Ignore neighboring modules, pyc files and model-serialized Python objects.
    sources = {n: checked_bytes(root / 'vendor' / n, check) for n, check in spec['sources'].items()}
    package_name = '_solarcheck_cvut_reference'
    package = types.ModuleType(package_name)
    package.__path__ = []
    sys.modules[package_name] = package
    for name in ('unet_parts', 'unet_model'):
        key = 'unet/' + name + '.py'
        module = types.ModuleType(package_name + '.' + name)
        module.__file__ = str(root / 'vendor' / key)
        sys.modules[module.__name__] = module
        exec(compile(sources[key], module.__file__, 'exec'), module.__dict__)
        setattr(package, name, module)
    return package.unet_model.UNet(n_channels=3, n_classes=2, bilinear=False).cpu().eval()


def checked_state(torch, data, model, spec):
    # Explicit restricted loading; never allow globals/fallback to arbitrary pickle.
    state = torch.load(BytesIO(data), map_location='cpu', weights_only=True)
    if type(state) not in (dict, OrderedDict):
        raise ValueError('CVUT benoetigt ein reines Gewichtswoerterbuch.')
    state = state.copy()
    values = state.pop('mask_values', None)
    if values is not None and (type(values) not in (list, tuple)
                              or list(values) not in ([0, 1], [0, 255])
                              or any(type(v) is not int for v in values)):
        raise ValueError('Unbekannte CVUT-Maskenklassenzuordnung.')
    expected = spec['state_shapes']
    if set(state) != set(expected) or set(model.state_dict()) != set(expected):
        raise ValueError('CVUT-Schichten stimmen nicht vollstaendig mit der Referenz ueberein.')
    for key, value in state.items():
        dtype = torch.int64 if key.endswith('num_batches_tracked') else torch.float32
        if (type(value) is not torch.Tensor or list(value.shape) != expected[key]
                or value.shape != model.state_dict()[key].shape or value.dtype != dtype
                or value.device.type != 'cpu' or not torch.isfinite(value).all().item()):
            raise ValueError('Ungueltiger CVUT-Gewichtstensor.')
    model.load_state_dict(state, strict=True)
    return values


def components(probabilities, shape, spec):
    """Fixed candidate opening/components, then existing native ROI/GIS filters."""
    height, width = shape[:2]
    expected = (spec['input_height'], spec['input_width'])
    if (probabilities.shape != expected or not np.isfinite(probabilities).all()
            or np.any((probabilities < 0) | (probabilities > 1))):
        raise ValueError('Ungueltige CVUT-Vordergrundwahrscheinlichkeiten.')
    binary = (probabilities >= spec['mask_threshold']).astype(np.uint8)
    kernel = np.ones((spec['opening_size'], spec['opening_size']), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if count > 2001:
        raise ValueError('Zu viele CVUT-Komponenten; kleineren Ausschnitt verwenden.')
    found = []
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if area < 4 or x == 0 or y == 0 or x+w >= expected[1] or y+h >= expected[0]:
            continue
        mask = (labels == index).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) != 1 or cv2.contourArea(contours[0]) < 4:
            continue
        polygon = cv2.boxPoints(cv2.minAreaRect(contours[0])).astype(np.float64)
        polygon[:, 0] = (polygon[:, 0] + .5) * width / expected[1] - .5
        polygon[:, 1] = (polygon[:, 1] + .5) * height / expected[0] - .5
        if np.any(polygon < 0) or np.any(polygon[:,0] > width-1) or np.any(polygon[:,1] > height-1):
            continue
        found.append(ModuleDetection(tuple(tuple(float(v) for v in p) for p in polygon),
                                     float(probabilities[labels == index].mean())))
    return tuple(found)


class CVUTModuleDetector:
    def __init__(self, path):
        self.root, _, self.spec = validate_manifest(path)
        data = self._check_weights()
        import torch
        if torch.__version__ != self.spec['torch_version'] or torch.version.cuda is not None:
            raise RuntimeError('Gepruefte getrennte CVUT-PyTorch-CPU-Version erforderlich.')
        torch.set_num_threads(2)
        self.torch = torch
        self.model = reference_model(self.root, self.spec, torch)
        self.mask_values = checked_state(torch, data, self.model, self.spec)
        self.name = 'cvut-unet-rgb-cpu-candidate'
        self.description = dict(provider='CVUT / U-Net candidate', model_version='rgb-observed-20261120',
            profile=PROFILE, source_commit=self.spec['source_commit'], code_license=self.spec['code_license'],
            weights_sha256=self.spec['weights_sha256'], backend='pytorch-cpu-'+self.spec['torch_version'],
            preprocessing=self.spec['preprocessing'], preprocessing_verified=False,
            class_mapping_verified=False, evaluation_allowed=True, production_approved=False,
            notice='Experimenteller Kandidat: Eingabe/Klassenzuordnung und Produktions-/Weitergaberechte noch offen.')

    def _check_weights(self):
        return checked_bytes(self.root / self.spec['weights'],
                             dict(bytes=self.spec['weights_bytes'], sha256=self.spec['weights_sha256']))

    def probabilities(self, image):
        if (image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3
                or min(image.shape[:2]) < 1 or max(image.shape[:2]) > 2048):
            raise ValueError('Begrenzter uint8-RGB-Ausschnitt erforderlich.')
        # Explicit candidate: BGR -> RGB unit floats, fixed paper dimensions.
        # This preprocessing has NOT been established as the original CVUT code.
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (self.spec['input_width'], self.spec['input_height']), interpolation=cv2.INTER_CUBIC)
        tensor = self.torch.from_numpy(np.ascontiguousarray(rgb.transpose(2,0,1))).float().div(255).unsqueeze(0)
        with self.torch.inference_mode():
            logits = self.model(tensor)
            if tuple(logits.shape) != (1, 2, self.spec['input_height'], self.spec['input_width']):
                raise ValueError('CVUT muss zwei Klassenlogits liefern.')
            if not self.torch.isfinite(logits).all().item():
                raise ValueError('CVUT liefert ungueltige Logits.')
            result = self.torch.softmax(logits, dim=1)[0,self.spec['foreground_channel']].cpu().numpy().copy()
        self._check_weights()
        return result

    def detect_array(self, image):
        return components(self.probabilities(image), image.shape, self.spec)
