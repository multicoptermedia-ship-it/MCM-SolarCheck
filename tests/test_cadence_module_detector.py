from mcm_solarcheck.vision.cadence_module_detector import CadenceConfirmedModuleDetector

def test_missing_image_fails_closed(tmp_path):
 assert CadenceConfirmedModuleDetector().detect(tmp_path/'missing.jpg')==()

def test_detector_has_stable_name():
 assert CadenceConfirmedModuleDetector().name=='cadence_confirmed_pv_module_v1'


def test_detector_keeps_configured_iou_for_ambiguity_gate(monkeypatch,tmp_path):
 import numpy as np
 import cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 path=tmp_path/'frame.jpg';cv2.imwrite(str(path),np.zeros((40,60,3),dtype=np.uint8))
 captured={}
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:())
 detector=CadenceConfirmedModuleDetector(minimum_iou=.37)
 monkeypatch.setattr(detector.image_detector,'detect',lambda path:())
 def gate(families,support,lines,width,height,*,minimum_iou):
  captured.update(width=width,height=height,minimum_iou=minimum_iou)
  from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
  return CadenceGateResult(False,(),'test_reject')
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',gate)
 assert detector.detect(path)==()
 assert captured=={'width':60,'height':40,'minimum_iou':.37}
