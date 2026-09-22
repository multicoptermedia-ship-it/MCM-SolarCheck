import cv2,numpy as np
from mcm_solarcheck.vision.grid_module_backend import GridModuleDetector

def test_grid_backend_detects_drawn_module_lattice(tmp_path):
 im=np.full((600,800,3),230,np.uint8)
 for x in (100,250,400,550): cv2.line(im,(x,100),(x,500),(20,20,20),5)
 for y in (100,300,500): cv2.line(im,(100,y),(550,y),(20,20,20),5)
 p=tmp_path/"grid.jpg";cv2.imwrite(str(p),im)
 d=GridModuleDetector(max_dimension=800).detect(p)
 assert len(d)>=4

def test_grid_backend_missing_file_fails_closed(tmp_path):
 assert GridModuleDetector().detect(tmp_path/"missing.jpg")==()
