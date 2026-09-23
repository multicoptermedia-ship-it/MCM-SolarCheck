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


def test_detector_rejects_negative_resolved_phase(monkeypatch,tmp_path):
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
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted_by_unique_lattice_evidence',(-1,0)))
 monkeypatch.setattr(module,'grid_module_detections',lambda *a,**k:(_ for _ in ()).throw(AssertionError('invalid phase must fail closed')))
 assert detector.detect(path)==()


def _detector_gate_case(monkeypatch,tmp_path,axes):
 import numpy as np
 import cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
 path=tmp_path/'gate-case.jpg';cv2.imwrite(str(path),np.zeros((40,40,3),dtype=np.uint8))
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:())
 detector=CadenceConfirmedModuleDetector()
 monkeypatch.setattr(detector.image_detector,'detect',lambda path:())
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted'))
 monkeypatch.setattr(module,'select_cadence_phase',lambda *a,**k:(_ for _ in ()).throw(AssertionError('invalid gate geometry must fail closed')))
 return detector.detect(path)

def test_detector_rejects_accepted_gate_with_wrong_axis_count(monkeypatch,tmp_path):
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 axes=(GridCadence(True,'test',10.0,3),)
 assert _detector_gate_case(monkeypatch,tmp_path,axes)==()

def test_detector_rejects_accepted_gate_with_invalid_multiple(monkeypatch,tmp_path):
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 axes=(GridCadence(True,'test',10.0,1),GridCadence(True,'test',10.0,4))
 assert _detector_gate_case(monkeypatch,tmp_path,axes)==()

def test_detector_rejects_accepted_gate_with_nonfinite_gap(monkeypatch,tmp_path):
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 axes=(GridCadence(True,'test',float('nan'),3),GridCadence(True,'test',10.0,4))
 assert _detector_gate_case(monkeypatch,tmp_path,axes)==()


def test_detector_rejects_invalid_configuration_before_image_work(monkeypatch,tmp_path):
 import mcm_solarcheck.vision.cadence_module_detector as module
 monkeypatch.setattr(module.cv2,'imread',lambda *a,**k:(_ for _ in ()).throw(AssertionError('invalid config must fail first')))
 assert CadenceConfirmedModuleDetector(max_dimension=0).detect(tmp_path/'x.jpg')==()
 assert CadenceConfirmedModuleDetector(max_dimension=True).detect(tmp_path/'x.jpg')==()
 assert CadenceConfirmedModuleDetector(minimum_iou=float('nan')).detect(tmp_path/'x.jpg')==()
 assert CadenceConfirmedModuleDetector(minimum_iou=1.1).detect(tmp_path/'x.jpg')==()

def test_detector_rejects_noninteger_resolved_phase(monkeypatch,tmp_path):
 import numpy as np,cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
 path=tmp_path/'phase-type.jpg';cv2.imwrite(str(path),np.zeros((80,80,3),dtype=np.uint8))
 families=(GridLineFamily(0,tuple(GridLine(0,x,1,10) for x in range(0,80,10))),GridLineFamily(90,tuple(GridLine(90,x,1,10) for x in range(0,80,10))))
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:families)
 detector=CadenceConfirmedModuleDetector();monkeypatch.setattr(detector.image_detector,'detect',lambda path:())
 axes=(GridCadence(True,'test',10.0,3),GridCadence(True,'test',10.0,4))
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted',(True,0)))
 monkeypatch.setattr(module,'grid_module_detections',lambda *a,**k:(_ for _ in ()).throw(AssertionError('invalid phase')))
 assert detector.detect(path)==()

def test_detector_rejects_malformed_phase_selection(monkeypatch,tmp_path):
 import numpy as np,cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 from mcm_solarcheck.vision.cadence_phase_selection import CadencePhaseSelection
 path=tmp_path/'phase-family.jpg';cv2.imwrite(str(path),np.zeros((40,40,3),dtype=np.uint8))
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:())
 detector=CadenceConfirmedModuleDetector();monkeypatch.setattr(detector.image_detector,'detect',lambda path:())
 axes=(GridCadence(True,'test',10.0,3),GridCadence(True,'test',10.0,4))
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted'))
 monkeypatch.setattr(module,'select_cadence_phase',lambda *a,**k:CadencePhaseSelection(True,(),1.0,'accepted'))
 monkeypatch.setattr(module,'grid_module_detections',lambda *a,**k:(_ for _ in ()).throw(AssertionError('malformed selection')))
 assert detector.detect(path)==()

def test_detector_never_fuses_after_finite_support_removes_all_cells(monkeypatch,tmp_path):
 import numpy as np,cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 from mcm_solarcheck.vision.cadence_phase_selection import CadencePhaseSelection
 from mcm_solarcheck.pairing.grid_lines import GridLineFamily
 from mcm_solarcheck.vision.detection import ModuleDetection
 path=tmp_path/'finite-filter.jpg';cv2.imwrite(str(path),np.zeros((40,40,3),dtype=np.uint8))
 families=(GridLineFamily(0,()),GridLineFamily(90,()))
 selected=(GridLineFamily(0,()),GridLineFamily(90,()))
 support=(ModuleDetection(((0,0),(0,20),(20,20),(20,0)),.9),)
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:families)
 detector=CadenceConfirmedModuleDetector();monkeypatch.setattr(detector.image_detector,'detect',lambda path:support)
 axes=(GridCadence(True,'test',10.0,3),GridCadence(True,'test',10.0,4))
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted'))
 monkeypatch.setattr(module,'select_cadence_phase',lambda *a,**k:CadencePhaseSelection(True,selected,1.0,'accepted'))
 monkeypatch.setattr(module,'grid_module_detections',lambda *a,**k:support)
 monkeypatch.setattr(module,'filter_cells_by_finite_support',lambda *a,**k:())
 monkeypatch.setattr(module,'fuse_module_detections',lambda *a,**k:(_ for _ in ()).throw(AssertionError('image support must not recreate rejected cells')))
 assert detector.detect(path)==()


def test_detector_rejects_out_of_range_resolved_phase(monkeypatch,tmp_path):
 import numpy as np,cv2
 import mcm_solarcheck.vision.cadence_module_detector as module
 from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
 path=tmp_path/'phase-range.jpg';cv2.imwrite(str(path),np.zeros((80,80,3),dtype=np.uint8))
 families=(GridLineFamily(0,tuple(GridLine(0,x,1,10) for x in range(0,80,10))),GridLineFamily(90,tuple(GridLine(90,x,1,10) for x in range(0,80,10))))
 monkeypatch.setattr(module,'detect_structural_lines',lambda *a,**k:())
 monkeypatch.setattr(module,'extract_grid_line_families',lambda lines:families)
 detector=CadenceConfirmedModuleDetector();monkeypatch.setattr(detector.image_detector,'detect',lambda path:())
 axes=(GridCadence(True,'test',10.0,3),GridCadence(True,'test',10.0,4))
 monkeypatch.setattr(module,'assess_ambiguous_module_cadence',lambda *a,**k:CadenceGateResult(True,axes,'accepted',(99,0)))
 monkeypatch.setattr(module,'grid_module_detections',lambda *a,**k:(_ for _ in ()).throw(AssertionError('out-of-range phase')))
 assert detector.detect(path)==()

def test_detector_rejects_boolean_axis_multiple(monkeypatch,tmp_path):
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 axes=(GridCadence(True,'test',10.0,True),GridCadence(True,'test',10.0,4))
 assert _detector_gate_case(monkeypatch,tmp_path,axes)==()

def test_detector_rejects_nonpositive_axis_gap(monkeypatch,tmp_path):
 from mcm_solarcheck.vision.grid_cadence import GridCadence
 axes=(GridCadence(True,'test',0.0,3),GridCadence(True,'test',10.0,4))
 assert _detector_gate_case(monkeypatch,tmp_path,axes)==()
