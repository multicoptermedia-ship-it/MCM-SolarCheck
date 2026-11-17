"""Optional local ONNX instance-segmentation candidate, evaluation only.

Uses OpenCV DNN on CPU. No hubs, downloads, pickle, Python model plugins or
production approvals. The selected manifest records the operator's evaluation
rights review; it is not a legal or accuracy attestation.
"""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np

from ..review.model_manifest import ModelManifest, verify_weights_sha256
from ..services.thermal_partial_comparison import _local
from .detection import ModuleDetection

PROFILE = 'opencv-onnx-pv-instance-roi-1'


class OnnxModuleDetector:
    def __init__(self, manifest_path):
        path = _local(manifest_path)
        if path.stat().st_size > 32768:
            raise ValueError('Modellbeschreibung zu gross.')
        raw = path.read_bytes()
        data = json.loads(raw)
        self.manifest = ModelManifest(**data['model'])
        if (data.get('profile') != PROFILE or data.get('evaluation_allowed') is not True
                or data.get('task') != 'pv_module_instance_segmentation' or data.get('classes') != ['pv_module']
                or data.get('production_approved') is not False
                or not all(isinstance(data.get(k), str) and data[k].strip() for k in ('reviewer', 'rights_evidence'))
                or data.get('code_license') not in ('MIT', 'Apache-2.0', 'BSD-3-Clause')
                or self.manifest.license_id not in ('MIT', 'Apache-2.0', 'BSD-3-Clause', 'CC-BY-4.0')
                or self.manifest.modality != 'rgb' or self.manifest.backend != 'opencv-dnn-cpu'
                or self.manifest.preprocessing != 'rgb-unit-letterbox'
                or type(data.get('input_size')) is not int or not 64 <= data['input_size'] <= 1024):
            raise ValueError('Gepruefte RGB-ONNX-Modellbeschreibung fuer lokalen Vergleich erforderlich.')
        relative = Path(data['weights'])
        if relative.is_absolute() or len(relative.parts) != 1 or relative.suffix != '.onnx':
            raise ValueError('ONNX-Datei muss direkt neben der Modellbeschreibung liegen.')
        self.weights = _local(path.parent / relative)
        if self.weights.stat().st_size > 512*1024*1024 or not verify_weights_sha256(self.manifest, self.weights):
            raise ValueError('Modellgewichte stimmen nicht mit der geprueften Beschreibung ueberein.')
        content = self.weights.read_bytes()
        if sha256(content).hexdigest() != self.manifest.weights_sha256.lower():
            raise ValueError('Modellgewichte waehrend des Ladens veraendert.')
        try:
            import onnx
        except ImportError:
            raise RuntimeError('Optionale ONNX-Pruefbibliothek fehlt; Anleitung zum KI-Modellvergleich lesen.') from None
        model = onnx.load_model_from_string(content)
        # Self-contained standard ONNX only: external tensors and embedded
        # functions/custom operators are outside this small evaluation profile.
        if (model.functions or any(x.domain not in ('', 'ai.onnx') for x in model.opset_import)
                or len(model.graph.node) > 50000):
            raise ValueError('Eigenstaendiges Standard-ONNX-Modell erforderlich.')
        def check_graph(graph):
            for tensor in graph.initializer:
                if tensor.external_data or tensor.data_location == onnx.TensorProto.EXTERNAL:
                    raise ValueError('Externe ONNX-Tensordateien sind nicht zugelassen.')
            if graph.sparse_initializer:
                raise ValueError('Sparse ONNX-Tensoren ausserhalb dieses Vergleichsprofils.')
            for node in graph.node:
                for attr in node.attribute:
                    if attr.HasField('g') or attr.graphs:
                        raise ValueError('ONNX-Untergraphen ausserhalb dieses Vergleichsprofils.')
                    for tensor in ([attr.t] if attr.HasField('t') else []) + list(attr.tensors):
                        if tensor.external_data or tensor.data_location == onnx.TensorProto.EXTERNAL:
                            raise ValueError('Externe ONNX-Tensordateien sind nicht zugelassen.')
        check_graph(model.graph)
        onnx.checker.check_model(model)
        self.size = data['input_size']
        shapes = [tuple(d.dim_value for d in x.type.tensor_type.shape.dim) for x in model.graph.input]
        if shapes != [(1, 3, self.size, self.size)] or {x.name for x in model.graph.output} != {'boxes', 'scores', 'masks'}:
            raise ValueError('ONNX-Eingabe oder Instanzausgaben passen nicht zum Vergleichsprofil.')
        try:
            self.net = cv2.dnn.readNetFromONNX(np.frombuffer(content, dtype=np.uint8))
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except cv2.error:
            raise ValueError('ONNX-Modell mit installierter OpenCV-CPU-Laufzeit nicht kompatibel.') from None
        self.description = dict(model=asdict(self.manifest), profile=PROFILE,
            manifest_sha256=sha256(raw).hexdigest(), evaluation_allowed=True, production_approved=False,
            reviewer=data['reviewer'], rights_evidence=data['rights_evidence'], code_license=data['code_license'],
            runtime_version=cv2.__version__, onnx_version=onnx.__version__, input_size=self.size,
            task='pv_module_instance_segmentation', classes=['pv_module'])
        self.name = 'onnx-evaluation-' + sha256(raw).hexdigest()[:16]

    def detect_array(self, bgr):
        if bgr.dtype != np.uint8 or bgr.ndim != 3 or bgr.shape[2] != 3 or not 1 <= min(bgr.shape[:2]) <= max(bgr.shape[:2]) <= 2048:
            raise ValueError('Begrenzter nativer RGB-Ausschnitt erforderlich.')
        height, width = bgr.shape[:2]
        scale = min(self.size/width, self.size/height)
        rw, rh = max(1, round(width*scale)), max(1, round(height*scale))
        left, top = (self.size-rw)//2, (self.size-rh)//2
        image = np.zeros((self.size, self.size, 3), np.uint8)
        image[top:top+rh, left:left+rw] = cv2.resize(bgr, (rw, rh), interpolation=cv2.INTER_AREA)
        self.net.setInput(cv2.dnn.blobFromImage(image, 1/255., swapRB=True))
        try:
            boxes, scores, masks = self.net.forward(['boxes', 'scores', 'masks'])
        except cv2.error:
            raise ValueError('ONNX-Ausfuehrung fehlgeschlagen; keine Erkennung uebernommen.') from None
        boxes, scores, masks = np.asarray(boxes), np.asarray(scores).reshape(-1), np.asarray(masks)
        if (boxes.ndim != 2 or boxes.shape != (len(scores), 4) or len(scores) > 2000
                or masks.ndim != 3 or masks.shape[0] != len(scores) or not 2 <= min(masks.shape[1:]) <= max(masks.shape[1:]) <= 64
                or not all(np.isfinite(a).all() for a in (boxes, scores, masks))
                or any(np.any((a < 0) | (a > 1)) for a in (boxes, scores, masks))):
            raise ValueError('Ungueltige oder zu grosse ONNX-Instanzausgaben.')
        detections = []
        for box, score, mask in zip(boxes, scores, masks):
            if score < .25:  # Also skip zero-filled padding in fixed-size exports.
                continue
            if box[2] <= box[0] or box[3] <= box[1]:
                raise ValueError('Ungueltige ONNX-Instanzbox.')
            x0, y0, x1, y1 = box*self.size
            # Do not turn padding or clipped instances into complete modules.
            if x0 < left or y0 < top or x1 > left+rw or y1 > top+rh:
                continue
            binary = (mask >= .5).astype(np.uint8)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) != 1 or cv2.contourArea(contours[0]) <= 0:
                continue
            points = contours[0].reshape(-1, 2).astype(np.float32)
            points[:, 0] = ((x0 + (points[:, 0]+.5)/mask.shape[1]*(x1-x0)-left)*width/rw)-.5
            points[:, 1] = ((y0 + (points[:, 1]+.5)/mask.shape[0]*(y1-y0)-top)*height/rh)-.5
            polygon = cv2.boxPoints(cv2.minAreaRect(points))
            detections.append(ModuleDetection(tuple((float(x), float(y)) for x, y in polygon), float(score)))
        if not verify_weights_sha256(self.manifest, self.weights):
            raise ValueError('Modellgewichte seit Auswahl veraendert.')
        return tuple(detections)
