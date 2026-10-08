from pathlib import Path
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.confirmed_module_detector import ConfirmedModuleDetector

def d(x1,y1,x2,y2,c=.8):return ModuleDetection(((x1,y1),(x2,y1),(x2,y2),(x1,y2)),c)
class Fake:
 def __init__(self,items):self.items=items
 def detect(self,p):return self.items

def test_composite_requires_both_geometry_and_image_support():
 det=ConfirmedModuleDetector(Fake((d(0,0,100,200),d(300,0,400,200))),Fake((d(10,10,90,190),)))
 out=det.detect(Path("x"))
 assert len(out)==1 and out[0].polygon_px==d(0,0,100,200).polygon_px

def test_composite_fails_closed_without_grid():
 assert ConfirmedModuleDetector(Fake(()),Fake((d(0,0,100,200),))).detect(Path("x"))==()
