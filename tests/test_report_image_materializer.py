from PIL import Image
import pytest
from mcm_solarcheck.reporting.image_crop import CropBox
from mcm_solarcheck.reporting.image_materializer import materialize_crop


def test_materialize_crop_preserves_requested_geometry(tmp_path):
    source=tmp_path/"source.png"; Image.new("RGB",(100,80)).save(source)
    target=materialize_crop(source,tmp_path/"crop.png",CropBox(10,20,50,60))
    with Image.open(target) as image: assert image.size==(40,40)


def test_materialize_crop_rejects_box_beyond_actual_source(tmp_path):
    source=tmp_path/"source.png"; Image.new("RGB",(20,20)).save(source)
    with pytest.raises(ValueError,match="exceeds"):
        materialize_crop(source,tmp_path/"crop.png",CropBox(0,0,21,20))


def test_materialize_crop_requires_real_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        materialize_crop(tmp_path/"missing.png",tmp_path/"crop.png",CropBox(0,0,10,10))
