import pytest
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_fusion import fuse_module_detections

def d(x1,y1,x2,y2,c=.8):return ModuleDetection(((x1,y1),(x2,y1),(x2,y2),(x1,y2)),c)

def test_support_confirms_grid_geometry_without_replacing_polygon():
 p=d(100,100,300,400);s=d(120,120,290,390,.9)
 out=fuse_module_detections((p,),(s,))
 assert len(out)==1 and out[0].polygon_px==p.polygon_px
 assert out[0].confidence>.9

def test_unconfirmed_grid_cell_is_rejected():
 assert fuse_module_detections((d(100,100,300,400),),(d(500,500,700,800),))==()

def test_support_cannot_create_module_without_grid_geometry():
 assert fuse_module_detections((),(d(100,100,300,400),))==()

def test_missing_support_fails_closed_by_default():
 p=d(100,100,300,400)
 assert fuse_module_detections((p,),())==()
 assert fuse_module_detections((p,),(),allow_primary_without_support=True)==(p,)

def test_invalid_threshold_rejected():
 with pytest.raises(ValueError):fuse_module_detections((),(),minimum_iou=2)
