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


MANUAL = ((600, 60), (660, 60), (660, 140), (600, 140))
ADDED = ((600, 350), (660, 350), (660, 430), (600, 430))


def test_manual_correction_addition_preserve_ids_history_and_reopen_without_detection(module_scene, monkeypatch):
    source, value = module_scene
    original_bytes = {p: p.read_bytes() for p in (value.rgb_path, value.thermal_path, source / 'job.json')}
    result = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    key = pv.region_key(result.rgb_window)
    region = pv.make_region(value, result)
    entry = region['entries'][0]
    entry.update(status='rejected', note='Synthetic partial outline rejected')
    ids = [e['module_id'] for e in region['entries']]
    original = json.dumps(region, sort_keys=True)
    monkeypatch.setattr(pv, '_detect_orthophoto_pv_pair', lambda *a, **k: pytest.fail('No new detection'))
    revised = pv.manual_module_outline(value, region, MANUAL, module_id=ids[0])
    assert json.dumps(region, sort_keys=True) == original  # No in-place mutation.
    assert revised['entries'][0]['status'] == 'pending'
    assert revised['entries'][0]['note'] == entry['note']
    assert revised['entries'][0]['history'][0]['status'] == 'rejected'
    assert revised['entries'][0]['history'][0]['proposal'] == entry['proposal']
    assert revised['entries'][1]['proposal'] == region['entries'][1]['proposal']
    revised = pv.manual_module_outline(value, revised, ADDED)
    assert [e['module_id'] for e in revised['entries'][:2]] == ids
    assert revised['entries'][2]['module_id'].endswith(':M-0003')
    assert revised['entries'][2]['origin'] == 'manual'
    for e in (revised['entries'][0], revised['entries'][2]):
        assert e['proposal']['confidence'] == 0
        assert e['proposal']['thermal_valid_coverage'] == 1
        # Same CRS / half-resolution Thermal, including pixel-center conversion.
        assert e['proposal']['thermal_polygon_px'][0] == pytest.approx(
            tuple((v+.5)/2-.5 for v in e['proposal']['rgb_polygon_px'][0]))
    revised['entries'][0]['status'] = 'outline_ok'
    stored = pv.save_module_review(value, {key: revised}, key)
    reopened = comparison.open_partial_comparison(source)
    restored, selected = pv.load_module_review(reopened)
    assert selected == key and restored[key] == revised
    assert stored['physical_module_ids_confirmed'] is False
    assert all(stored[k] is False for k in comparison.FLAGS)
    assert all(p.read_bytes() == data for p, data in original_bytes.items())
    with pytest.raises(ValueError, match='Paarimport gesperrt'):
        detect_orthophoto_pv_window(value.rgb_path, value.thermal_path, window=result.rgb_window)


@pytest.mark.parametrize('polygon', [
    ((600, 60), (660, 140), (660, 60), (600, 140)),
    ((19, 60), (60, 60), (60, 140), (19, 140)),
    ((600, 60), (620, 60), (640, 60), (660, 60)),
    ((600, 60), (float('nan'), 60), (660, 140), (600, 140)),
])
def test_invalid_manual_polygon_does_not_replace_saved_review(module_scene, polygon):
    _, value = module_scene
    result = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    key = pv.region_key(result.rgb_window)
    region = pv.make_region(value, result)
    pv.save_module_review(value, {key: region}, key)
    saved = (value.folder / pv.STATE).read_bytes()
    with pytest.raises(ValueError):
        pv.manual_module_outline(value, region, polygon)
    assert (value.folder / pv.STATE).read_bytes() == saved
    with pytest.raises(ValueError, match='ueberlappt'):
        pv.manual_module_outline(value, region, result.proposals[0].rgb_polygon_px)


def test_manual_rgb_mask_thermal_gap_cancel_and_source_change(module_scene, monkeypatch):
    source, value = module_scene
    # A real synthetic GDAL mask, then consciously reopen the changed test source.
    with rasterio.open(value.rgb_path, 'r+') as raster:
        mask = np.full((raster.height, raster.width), 255, np.uint8)
        mask[70:80, 610:620] = 0
        raster.write_mask(mask)
    value = comparison.open_partial_comparison(source, value.rgb_path)
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='looks_aligned', note='Synthetic')
    result = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    region = pv.make_region(value, result)
    with pytest.raises(ValueError, match='RGB-Pixel'):
        pv.manual_module_outline(value, region, MANUAL)
    gap = ((50, 400), (100, 400), (100, 480), (50, 480))
    revised = pv.manual_module_outline(value, region, gap)
    assert revised['entries'][-1]['proposal']['thermal_valid_coverage'] == 0
    with pytest.raises(RuntimeError, match='cancelled|abgebrochen'):
        pv.manual_module_outline(None, region, gap, should_cancel=lambda: True)
    coverage = pv._thermal_coverage
    cancelled = False
    def interrupted(*args):
        nonlocal cancelled
        answer = coverage(*args)
        cancelled = True
        return answer
    monkeypatch.setattr(pv, '_thermal_coverage', interrupted)
    with pytest.raises(RuntimeError, match='cancelled|abgebrochen'):
        pv.manual_module_outline(value, region, gap, should_cancel=lambda: cancelled)
    def changed(*args):
        answer = coverage(*args)
        with rasterio.open(value.rgb_path, 'r+') as raster:
            raster.update_tags(SYNTHETIC_CHANGED='true')
        return answer
    monkeypatch.setattr(pv, '_thermal_coverage', changed)
    with pytest.raises(ValueError):
        pv.manual_module_outline(value, region, gap)
    assert not (value.folder / pv.STATE).exists()


def test_manual_history_and_id_tampering_rejected_and_empty_region_supported(module_scene):
    _, value = module_scene
    result = pv.OrthophotoPVWindowResult((), (20, 20, 760, 560), 'manual')
    region = pv.make_region(value, result)
    region = pv.manual_module_outline(value, region, MANUAL)
    module_id = region['entries'][0]['module_id']
    region['entries'][0]['status'] = 'outline_ok'
    region = pv.manual_module_outline(value, region, ADDED, module_id=module_id)
    assert region['entries'][0]['history'][0]['status'] == 'outline_ok'
    region['entries'][0]['history'][0]['proposal']['thermal_calibration_verified'] = True
    with pytest.raises(ValueError):
        pv.parse_region(value, region)


def test_legacy_saved_review_upgrades_without_losing_ids_or_notes(module_scene):
    _, value = module_scene
    result = pv.detect_partial_pv_window(value, window=(20, 20, 760, 560))
    key = pv.region_key(result.rgb_window)
    region = pv.make_region(value, result)
    region['entries'][0].update(status='rejected', note='Synthetic legacy rejection')
    record = pv.save_module_review(value, {key: region}, key)
    record['check'] = pv.LEGACY_CHECK
    for entry in record['regions'][key]['entries']:
        del entry['origin'], entry['history']
    (value.folder / pv.STATE).write_text(json.dumps(record))
    restored, selected = pv.load_module_review(value)
    assert restored[key]['entries'][0]['status'] == 'rejected'
    assert restored[key]['entries'][0]['note'] == 'Synthetic legacy rejection'
    updated = pv.manual_module_outline(value, restored[key], MANUAL,
        module_id=restored[key]['entries'][0]['module_id'])
    assert updated['entries'][0]['history'][0]['note'] == 'Synthetic legacy rejection'
    saved = pv.save_module_review(value, {key: updated}, selected)
    assert saved['check'] == pv.CHECK
    updated['entries'][0]['module_id'] = updated['entries'][1]['module_id']
    with pytest.raises(ValueError):
        pv.parse_region(value, updated)
