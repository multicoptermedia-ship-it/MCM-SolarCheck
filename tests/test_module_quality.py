import pytest
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_quality import assess_module_detection,filter_module_detections

def det(poly,confidence=.9): return ModuleDetection(tuple(poly),confidence)

def test_accepts_plausible_module():
    q=assess_module_detection(det(((100,100),(300,100),(300,500),(100,500))),4000,3000)
    assert q.accepted and q.reason=="accepted"

@pytest.mark.parametrize("poly,reason",[
    (((-1,10),(20,10),(20,30)), "outside_image"),
    (((10,10),(20,20),(30,30)), "degenerate_polygon"),
    (((10,10),(11,10),(11,11),(10,11)), "too_small"),
])
def test_rejects_invalid_geometry(poly,reason):
    assert assess_module_detection(det(poly),4000,3000).reason==reason

def test_suppresses_duplicate_and_keeps_higher_confidence():
    a=det(((100,100),(300,100),(300,500),(100,500)),.95)
    b=det(((105,105),(305,105),(305,505),(105,505)),.80)
    kept=filter_module_detections((b,a),4000,3000)
    assert kept==(a,)

def test_keeps_distinct_neighboring_modules():
    a=det(((100,100),(300,100),(300,500),(100,500)))
    b=det(((320,100),(520,100),(520,500),(320,500)))
    assert len(filter_module_detections((a,b),4000,3000))==2

def test_wrong_class_is_not_a_module():
    roof=ModuleDetection(((100,100),(300,100),(300,500),(100,500)),.99,"roof")
    assert filter_module_detections((roof,),4000,3000)==()

def test_invalid_dimensions_fail():
    with pytest.raises(ValueError): assess_module_detection(det(((0,0),(1,0),(1,1))),0,3000)
