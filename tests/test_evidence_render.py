from PIL import Image
from mcm_solarcheck.reporting.evidence import EvidenceImagePlan
from mcm_solarcheck.reporting.evidence_render import render_evidence


def make_image(path,size):Image.new('RGB',size,(100,120,140)).save(path)


def test_renders_thermal_and_validated_rgb_crops_without_touching_sources(tmp_path):
    thermal=tmp_path/'T.jpg';rgb=tmp_path/'V.jpg';make_image(thermal,(640,512));make_image(rgb,(4000,3000))
    thermal_before=thermal.read_bytes();rgb_before=rgb.read_bytes()
    plan=EvidenceImagePlan('F-1',thermal,(320,256),rgb,(2000,1500),.99,'homography','assigned',2.0,'M-1')
    result=render_evidence(plan,tmp_path/'out')
    assert result.thermal_image.exists();assert result.rgb_image is not None and result.rgb_image.exists()
    assert thermal.read_bytes()==thermal_before;assert rgb.read_bytes()==rgb_before
    assert Image.open(result.thermal_image).size==(240,240);assert Image.open(result.rgb_image).size==(1000,1000)


def test_without_rgb_marker_only_thermal_evidence_is_rendered(tmp_path):
    thermal=tmp_path/'T.jpg';rgb=tmp_path/'V.jpg';make_image(thermal,(640,512));make_image(rgb,(4000,3000))
    plan=EvidenceImagePlan('F-2',thermal,(20,20),rgb,None,.9,'homography','ambiguous_edge',3.0,None)
    result=render_evidence(plan,tmp_path/'out')
    assert result.thermal_image.exists();assert result.rgb_image is None


def test_crop_is_clamped_at_image_boundary(tmp_path):
    thermal=tmp_path/'T.jpg';make_image(thermal,(640,512))
    plan=EvidenceImagePlan('F-3',thermal,(5,5))
    result=render_evidence(plan,tmp_path/'out',thermal_half_size=120)
    assert Image.open(result.thermal_image).size==(125,125)
