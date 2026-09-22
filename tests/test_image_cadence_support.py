from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.image_cadence_support import image_module_intervals

def d(x0,y0,x1,y1):return ModuleDetection(((x0,y0),(x1,y0),(x1,y1),(x0,y1)),.8)

def test_projects_independent_detection_spans_on_grid_axis():
 ds=(d(0,0,30,20),d(50,0,80,20))
 assert image_module_intervals(ds,0)==(30.0,30.0)
 assert image_module_intervals(ds,90)==(20.0,20.0)

def test_empty_support_stays_empty():
 assert image_module_intervals((),0)==()
