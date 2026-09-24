import pytest
from mcm_solarcheck.review.yolo_export import yolo_detection_line


def test_yolo_detection_line_normalizes_reviewed_box():
    assert yolo_detection_line("hotspot",{"hotspot":2},(100,50,300,150),400,200)=="2 0.5000000000 0.5000000000 0.5000000000 0.5000000000"


def test_yolo_detection_line_rejects_unknown_class():
    with pytest.raises(ValueError,match="no YOLO class id"):
        yolo_detection_line("unknown",{"hotspot":0},(1,1,2,2),10,10)


def test_yolo_detection_line_rejects_out_of_bounds_box():
    with pytest.raises(ValueError,match="outside source image bounds"):
        yolo_detection_line("hotspot",{"hotspot":0},(0,0,11,10),10,10)
