import pytest
from mcm_solarcheck.reporting.image_crop import CropBox, polygon_crop_box


def test_polygon_crop_adds_padding_and_clamps_to_image():
    box=polygon_crop_box(((2,3),(20,3),(20,15),(2,15)),100,80,padding_fraction=0.1)
    assert box.left==0
    assert box.top==1
    assert box.right>20 and box.bottom>15
    assert box.right<=100 and box.bottom<=80


def test_polygon_crop_rejects_invalid_geometry():
    with pytest.raises(ValueError): polygon_crop_box(((1,1),(2,2)),100,100)
    with pytest.raises(ValueError): polygon_crop_box(((1,1),(2,float("nan")),(3,3)),100,100)
    with pytest.raises(ValueError): CropBox(5,5,4,10)


def test_polygon_crop_rejects_polygon_fully_outside_frame():
    with pytest.raises(ValueError,match="outside"):
        polygon_crop_box(((200,200),(220,200),(220,220),(200,220)),100,100)
