import pytest
from mcm_solarcheck.review.training_geometry import ReviewedGeometry


def test_reviewed_box_supports_detection():
    value=ReviewedGeometry("T1","inspector","rendered_rgb",box_xyxy=(1,2,20,30))
    assert value.task_support==frozenset({"detection"})


def test_reviewed_polygon_supports_segmentation():
    value=ReviewedGeometry("T1","inspector","grayscale_8bit",polygon_px=((1,1),(10,1),(5,9)))
    assert value.task_support==frozenset({"segmentation"})


def test_combined_geometry_supports_both_tasks():
    value=ReviewedGeometry("T1","inspector","rendered_rgb",box_xyxy=(1,1,10,10),polygon_px=((1,1),(10,1),(5,9)))
    assert value.task_support==frozenset({"detection","segmentation"})


@pytest.mark.parametrize("kwargs",[
    {},
    {"box_xyxy":(1,1,1,10)},
    {"box_xyxy":(1,1,float("nan"),10)},
    {"polygon_px":((1,1),(2,2))},
])
def test_invalid_geometry_fails_closed(kwargs):
    with pytest.raises(ValueError):
        ReviewedGeometry("T1","inspector","rendered_rgb",**kwargs)


def test_raw_radiometric_geometry_is_not_training_geometry():
    with pytest.raises(ValueError,match="rendered representation"):
        ReviewedGeometry("T1","inspector","radiometric_raw",box_xyxy=(1,1,10,10))
