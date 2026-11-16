"""Existing native-resolution detector and local draft IDs on synthetic rasters only."""
import json
import shutil

import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin

from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_comparison as comparison
from mcm_solarcheck.services.orthophoto_pv_modules import detect_orthophoto_pv_window
from mcm_solarcheck.services.opensfm_rgb_pilot import read_opensfm_metrics
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source
from test_gui_orthophoto_pv_review import _sources


@pytest.fixture
def module_scene(scene, tmp_path):
    source, folder, rgb, thermal = scene
    with rasterio.open(thermal) as raster:
        tags = raster.tags()
    generated = tmp_path / 'synthetic-module-sources'
    generated.mkdir()
    new_rgb, _ = _sources(generated)
    shutil.copyfile(new_rgb, rgb)
    with rasterio.open(thermal, 'w', driver='GTiff', width=400, height=300, count=4,
        dtype='uint8', crs='EPSG:25832', transform=from_origin(350000, 5650000, .2, .2)) as raster:
        values = np.full((4, 300, 400), 100, np.uint8)
        values[3] = 255
        values[3, :, :100] = 0  # First RGB module lacks Thermal support.
        raster.write(values)
        raster.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
        raster.update_tags(**tags)
    value = comparison.open_partial_comparison(source, rgb)
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='looks_aligned', note='Synthetic visual comparison')
    return source, value


def test_actual_detector_drafts_masks_detail_save_reopen_and_regular_gate(module_scene, monkeypatch):
    source, value = module_scene
    import cv2
    monkeypatch.setattr(cv2, 'imread', lambda *a, **k: pytest.fail('Only bounded rasterio ROI reads'))
    originals = {p: p.read_bytes() for p in (value.rgb_path, value.thermal_path, source / 'job.json')}
    result = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    assert len(result.proposals) == 2
    first = min(result.proposals, key=lambda p: min(x for x, _ in p.rgb_polygon_px))
    second = max(result.proposals, key=lambda p: min(x for x, _ in p.rgb_polygon_px))
    assert first.thermal_valid_coverage == 0 and second.thermal_valid_coverage == 1
    rgb, heat = pv.partial_module_detail(value, first)
    assert rgb.shape == heat.shape and np.isnan(heat).all()
    rgb, heat = pv.partial_module_detail(value, second)
    assert np.isfinite(heat).all() and rgb.shape[:2] != value.rgb.shape[:2]
    ids = pv.draft_module_ids(value, result)
    assert len(set(ids)) == 2 and all(':20-20-760-560:M-' in k for k in ids)
    region = pv.make_region(value, result, {ids[0]: dict(status='outline_ok', note='Synthetic edge review')})
    key = pv.region_key(result.rgb_window)
    stored = pv.save_module_review(value, {key: region}, key)
    assert all(stored[k] is False for k in comparison.FLAGS)
    assert stored['physical_module_ids_confirmed'] is False
    reopened = comparison.open_partial_comparison(source)
    regions, selected = pv.load_module_review(reopened)
    restored, canonical = pv.parse_region(reopened, regions[selected])
    assert selected == key and pv.draft_module_ids(reopened, restored) == ids
    assert canonical['entries'][0]['note'] == 'Synthetic edge review'
    assert canonical['entries'][0]['status'] == 'outline_ok'
    assert all(p.read_bytes() == data for p, data in originals.items())
    assert result.summary()['thermal_values_interpreted'] is False
    with pytest.raises(ValueError, match='Paarimport gesperrt'):
        detect_orthophoto_pv_window(value.rgb_path, value.thermal_path, window=(20, 20, 760, 560))
    metrics = json.dumps(read_opensfm_metrics(source))
    assert 'Synthetic edge review' not in metrics and ids[0] not in metrics


def test_different_roi_scope_retains_old_ids_and_reviews_without_physical_identity_claim(module_scene):
    _, value = module_scene
    a = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    b = pv.detect_partial_pv_window(value, window=(0, 0, 800, 600))
    assert not set(pv.draft_module_ids(value, a)) & set(pv.draft_module_ids(value, b))
    ka, kb = pv.region_key(a.rgb_window), pv.region_key(b.rgb_window)
    regions = {ka: pv.make_region(value, a), kb: pv.make_region(value, b)}
    pv.save_module_review(value, regions, kb)
    restored, selected = pv.load_module_review(value)
    assert set(restored) == {ka, kb} and selected == kb


@pytest.mark.parametrize('failure', ['source_change', 'id', 'approval', 'geometry', 'review', 'note'])
def test_changed_sources_or_malformed_saved_drafts_do_not_resume(module_scene, failure):
    _, value = module_scene
    result = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    key = pv.region_key(result.rgb_window)
    record = pv.save_module_review(value, {key: pv.make_region(value, result)}, key)
    entry = record['regions'][key]['entries'][0]
    if failure == 'source_change':
        with rasterio.open(value.rgb_path, 'r+') as raster:
            raster.update_tags(SYNTHETIC_CHANGED='true')
    elif failure == 'id':
        entry['module_id'] = 'confirmed-module-1'
    elif failure == 'approval':
        entry['proposal']['module_analysis_verified'] = True
    elif failure == 'geometry':
        entry['proposal']['rgb_polygon_px'] = [[-1, -1], *entry['proposal']['rgb_polygon_px'][1:]]
    elif failure == 'review':
        entry['status'] = 'physically_confirmed'
    else:
        entry['note'] = 'x' * 1001
    (value.folder / pv.STATE).write_text(json.dumps(record))
    with pytest.raises(ValueError):
        pv.load_module_review(value)


def test_unreviewed_comparison_invalid_roi_and_cancel_do_not_start_detector(module_scene):
    _, value = module_scene
    with pytest.raises(ValueError, match='window'):
        pv.detect_partial_pv_window(None, window=(0, 0, 2049, 1))
    with pytest.raises(RuntimeError, match='abgebrochen'):
        pv.detect_partial_pv_window(None, window=(0, 0, 10, 10), should_cancel=lambda: True)
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='visible_offset', note='Synthetic offset')
    with pytest.raises(ValueError, match='passend'):
        pv.detect_partial_pv_window(value, window=(0, 0, 100, 100))
