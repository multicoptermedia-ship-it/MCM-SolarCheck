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


def test_detector_uses_resolved_phase_without_reselection(monkeypatch,tmp_path):
 import numpy as np
 import cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
 path=tmp_path/'frame.jpg';cv2.imwrite(str(path),np.zeros((80,80,3),dtype=np.uint8))
 families=(
  GridLineFamily(0,tuple(GridLine(0,x,1,10) for x in (0,10,20,30,40,50,60,70))),
  GridLineFamily(90,tuple(GridLine(90,x,1,10) for x in (0,10,20,30,40,50,60,70))),
 )
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:families)
 detector=CadenceConfirmedModuleDetector()
 monkeypatch.setattr(detector.image_detector,'detect',lambda path:())
 axes=(GridCadence(True,'uniquely_lattice_supported',10.0,3),GridCadence(True,'uniquely_lattice_supported',10.0,4))
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted_by_unique_lattice_evidence',(1,0)))
 monkeypatch.setattr(module,'select_cadence_phase',lambda *a,**k:(_ for _ in ()).throw(AssertionError('phase must not be reselected')))
 captured={}
 monkeypatch.setattr(module,'grid_module_detections',lambda selected,*a,**k:captured.setdefault('families',selected) or ())
 monkeypatch.setattr(module,'filter_cells_by_finite_support',lambda cells,*a,**k:())
 assert detector.detect(path)==()
 assert captured['families'][0].lines[0].offset_px==10
 assert captured['families'][1].lines[0].offset_px==0
