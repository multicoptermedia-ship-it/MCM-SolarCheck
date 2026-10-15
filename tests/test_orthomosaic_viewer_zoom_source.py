"""Guard the shared orthomosaic viewer against independent RGB/thermal transforms.

These are source integration checks, not browser or photogrammetry acceptance tests.
"""
from pathlib import Path

VIEWER = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


def test_zoom_and_pan_transform_both_registered_layers_together():
    html = VIEWER.read_text(encoding="utf-8")
    assert "rgb.style.transform=transform;thermal.style.transform=transform;" in html
    assert "zoomTo(scale*1.25)" in html
    assert "zoomTo(scale/1.25)" in html
    assert "stage.addEventListener('wheel'" in html
    assert "stage.addEventListener('pointermove'" in html
    assert "Math.max(1,Math.min(8," in html


def test_reveal_clips_layer_not_individual_transformed_image():
    html = VIEWER.read_text(encoding="utf-8")
    assert 'id="ortho-thermal-layer"' in html
    assert "thermalLayer.style.clipPath=" in html
    assert "thermal.style.clipPath=" not in html
    assert "divider.style.left=value+'%'" in html


def test_viewer_still_requires_verified_registered_layers():
    html = VIEWER.read_text(encoding="utf-8")
    assert "manifest.registration_verified!==true" in html
    assert "manifest.thermal_is_visualization_only!==true" in html
    assert "stage.hidden=true;slider.disabled=true" in html
    assert "stage.hidden=false;slider.disabled=false;offsetX=0;offsetY=0;zoomTo(1)" in html
