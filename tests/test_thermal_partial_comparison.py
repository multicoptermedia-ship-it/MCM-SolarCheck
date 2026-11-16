"""Synthetic local comparison, persistence and unchanged regular intake boundary."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mcm_solarcheck.services import thermal_partial_comparison as comparison
from mcm_solarcheck.services import opensfm_thermal_partial as partial
from mcm_solarcheck.services.orthophoto_layer_alignment import inspect_orthophoto_layer_pair
from mcm_solarcheck.services.opensfm_rgb_pilot import read_opensfm_metrics
from test_opensfm_sparse_bridge import sparse_source
from test_opensfm_thermal_partial import prepare
from test_opensfm_thermal_pilot import thermal_engine
from test_orthophoto_layer_alignment import _raster


@pytest.fixture
def scene(sparse_source):
    source, config = sparse_source
    prepare(source)
    folder, _ = partial.run_partial_preview(source, config, executor=thermal_engine([]))
    rgb = _raster(source.parent / 'finished-rgb.tif', np.full((3, 6, 8), 30, np.uint8),
                  transform=from_origin(500000, 5500000, .1, .1), crs='EPSG:32632')
    thermal = folder / 'undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif'
    return source, folder, rgb, thermal


def test_finished_preview_compares_without_changing_rasters_source_or_intake_gate(scene):
    source, folder, rgb, thermal = scene
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    fingerprints = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)}
    with rasterio.open(thermal, 'r+') as dst:
        dst.transform = from_origin(500000.2, 5500000, .1, .1)
    fingerprints[thermal] = hashlib.sha256(thermal.read_bytes()).hexdigest()
    value = comparison.open_partial_comparison(source, rgb)
    assert value.label == 'unvollständig: 8 von 10 Bildern'
    assert value.rgb.shape == value.thermal.shape == (6, 8, 3)
    assert np.isnan(value.thermal[:, :2]).all()
    assert np.isfinite(value.thermal[:, 2:]).all()
    assert not (folder / comparison.STATE).exists()
    saved = comparison.save_partial_comparison(value, opacity=75, zoom=1.25,
        verdict='looks_aligned', note='Synthetic local judgement, not a geometric approval')
    assert all(saved[k] is False for k in comparison.FLAGS)
    restored = comparison.open_partial_comparison(source)
    assert restored.view == dict(opacity=75, zoom=1.25, verdict='looks_aligned',
        note='Synthetic local judgement, not a geometric approval')
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in fingerprints.items())
    assert all(p.read_bytes() == data for p, data in before.items())
    assert set(before) == {p for p in source.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='Paarimport gesperrt'):
        inspect_orthophoto_layer_pair(rgb, thermal)
    metrics = json.dumps(read_opensfm_metrics(source))
    assert 'Synthetic local judgement' not in metrics and str(rgb) not in metrics


@pytest.mark.parametrize('failure', ['tag', 'rgb_partial', 'same_file', 'no_overlap', 'changed_rgb', 'changed_thermal'])
def test_wrong_preview_no_overlap_and_changed_saved_sources_are_rejected(scene, failure):
    source, folder, rgb, thermal = scene
    value = comparison.open_partial_comparison(source, rgb)
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='not_reviewed', note='')
    if failure == 'tag':
        with rasterio.open(thermal, 'r+') as dst:
            dst.update_tags(SOLARCHECK_LABEL='complete')
    elif failure == 'rgb_partial':
        with rasterio.open(rgb, 'r+') as dst:
            dst.update_tags(SOLARCHECK_INCOMPLETE='true')
    elif failure == 'no_overlap':
        with rasterio.open(rgb, 'r+') as dst:
            dst.transform = from_origin(600000, 5600000, .1, .1)
    elif failure.startswith('changed'):
        path = rgb if failure == 'changed_rgb' else thermal
        with rasterio.open(path, 'r+') as dst:
            dst.write(np.zeros((dst.height, dst.width), np.uint8), 1)
    with pytest.raises(ValueError):
        comparison.open_partial_comparison(source, thermal if failure == 'same_file' else
            None if failure.startswith('changed') else rgb)
    if failure.startswith('changed'):
        with pytest.raises(ValueError, match='veraendert'):
            comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='not_reviewed', note='')


def test_alpha_missing_area_stays_missing_and_local_decision_never_sets_approval(scene):
    source, folder, rgb, thermal = scene
    with rasterio.open(thermal, 'r+') as dst:
        alpha = dst.read(4)
        alpha[:, :3] = 0
        dst.write(alpha, 4)
    value = comparison.open_partial_comparison(source, rgb)
    assert np.isnan(value.thermal[:, :3]).all()
    assert np.isfinite(value.thermal[:, 3:]).all()
    for verdict in comparison.VERDICTS:
        saved = comparison.save_partial_comparison(value, opacity=0, zoom=4, verdict=verdict, note='')
        assert all(saved[k] is False for k in comparison.FLAGS)
    with pytest.raises(ValueError):
        comparison.save_partial_comparison(value, opacity=101, zoom=1, verdict='looks_aligned', note='')
    with pytest.raises(ValueError):
        comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='looks_aligned', note='x' * 2001)
