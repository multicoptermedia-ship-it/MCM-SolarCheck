import cv2,numpy as np
from mcm_solarcheck.vision.grid_module_backend import GridModuleDetector
from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.grid_lines import extract_grid_line_families

def test_grid_backend_contract_uses_real_structural_stack(tmp_path,monkeypatch):
 im=np.full((600,800,3),230,np.uint8);p=tmp_path/"grid.jpg";cv2.imwrite(str(p),im)
 lines=tuple(StructuralLine(x,50,x,550,500,90) for x in (100,250,400,550))+tuple(StructuralLine(50,y,750,y,700,0) for y in (100,300,500))
 monkeypatch.setattr("mcm_solarcheck.vision.grid_module_backend.detect_structural_lines",lambda *a,**k:lines)
 d=GridModuleDetector(max_dimension=800).detect(p)
 assert len(d)==6

def test_grid_family_extraction_on_fixture_lines():
 lines=tuple(StructuralLine(x,50,x,550,500,90) for x in (100,250,400,550))+tuple(StructuralLine(50,y,750,y,700,0) for y in (100,300,500))
 f=extract_grid_line_families(lines)
 assert len(f)==2 and sorted(len(x.lines) for x in f)==[3,4]

def test_grid_backend_missing_file_fails_closed(tmp_path):
 assert GridModuleDetector().detect(tmp_path/"missing.jpg")==()


def test_grid_backend_exposes_finite_support_diagnostics(tmp_path,monkeypatch):
 im=np.full((600,800,3),230,np.uint8);p=tmp_path/"grid-diagnostics.jpg";cv2.imwrite(str(p),im)
 lines=tuple(StructuralLine(x,50,x,550,500,90) for x in (100,250,400,550))+tuple(StructuralLine(50,y,750,y,700,0) for y in (100,300,500))
 monkeypatch.setattr("mcm_solarcheck.vision.grid_module_backend.detect_structural_lines",lambda *a,**k:lines)
 detections,q=GridModuleDetector(max_dimension=800).detect_with_diagnostics(p)
 assert len(detections)==6
 assert q.raw_candidates==6 and q.supported_candidates==6
 assert q.structural_lines==7 and sorted(q.family_sizes)==[3,4]
