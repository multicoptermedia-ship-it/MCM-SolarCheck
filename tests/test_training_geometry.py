import pytest
from mcm_solarcheck.review.training_geometry import ReviewedGeometry, require_geometry_for_task, validate_geometry_bounds


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


def test_detection_task_rejects_polygon_only_geometry():
    value=ReviewedGeometry("T1","inspector","rendered_rgb",polygon_px=((1,1),(10,1),(5,9)))
    with pytest.raises(ValueError,match="does not support detection"):
        require_geometry_for_task(value,"detection")


def test_segmentation_task_rejects_box_only_geometry():
    value=ReviewedGeometry("T1","inspector","rendered_rgb",box_xyxy=(1,1,10,10))
    with pytest.raises(ValueError,match="does not support segmentation"):
        require_geometry_for_task(value,"segmentation")


def test_geometry_bounds_accept_exact_source_extent():
    value=ReviewedGeometry("T1","inspector","rendered_rgb",box_xyxy=(0,0,640,512))
    assert validate_geometry_bounds(value,640,512) is value


@pytest.mark.parametrize("box",[
    (-1,0,10,10),(0,-1,10,10),(0,0,641,10),(0,0,10,513)
])
def test_geometry_bounds_reject_out_of_image_box(box):
    value=ReviewedGeometry("T1","inspector","rendered_rgb",box_xyxy=box)
    with pytest.raises(ValueError,match="outside source image bounds"):
        validate_geometry_bounds(value,640,512)


def test_geometry_bounds_reject_out_of_image_polygon():
    value=ReviewedGeometry("T1","inspector","rendered_rgb",polygon_px=((1,1),(641,2),(3,4)))
    with pytest.raises(ValueError,match="polygon lies outside"):
        validate_geometry_bounds(value,640,512)
