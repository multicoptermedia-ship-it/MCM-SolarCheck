"""Saved corrections -> bounded local annotation preparation, synthetic only."""
from copy import deepcopy
import json

import pytest
import rasterio

from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_training as learning
from mcm_solarcheck.services import thermal_partial_comparison as comparison
from test_thermal_partial_pv import module_scene, MANUAL, ADDED
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source


def reviewed(value, window=(20, 20, 760, 560)):
    result = pv.detect_partial_pv_window(value, window=window)
    region = pv.make_region(value, result)
    for entry in region['entries']:
        entry['status'] = 'outline_ok'
    key = pv.region_key(window)
    return key, region


def save(value, key, **kwargs):
    return learning.save_learning_preparation(value, key, reviewer='Synthetic reviewer',
        group_id='Synthetic plant A', complete_annotation=True,
        expected_review_sha256=learning.read_learning_preparation(value, key)['review_sha256'], **kwargs)


def test_corrected_added_rejected_deleted_labels_geometry_identity_and_reopening(module_scene, monkeypatch):
    source, value = module_scene
    key, region = reviewed(value)
    original_id = region['entries'][0]['module_id']
    region = pv.manual_module_outline(value, region, MANUAL, module_id=original_id)
    region = pv.manual_module_outline(value, region, ADDED)
    region = pv.manual_module_outline(value, region, ((612, 75), (630, 75), (630, 95), (612, 95)))
    for entry in region['entries']:
        entry['status'] = 'outline_ok'
    region['entries'][1]['status'] = 'rejected'
    region['entries'][-1]['deleted'] = True
    pv.save_module_review(value, {key: region}, key)
    originals = {p: p.read_bytes() for p in (source / 'job.json', value.rgb_path, value.thermal_path,
        value.folder / pv.STATE, value.folder / comparison.STATE)}
    monkeypatch.setattr(pv, '_detect_orthophoto_pv_pair', lambda *a, **k: pytest.fail('No detection or model run'))
    result = save(value, key)
    manifest = result['manifest']
    assert len(manifest['labels']) == 2  # Current correction + addition, never rejected/deleted child.
    assert [v['draft_module_id'] for v in manifest['labels']] == [original_id, region['entries'][2]['module_id']]
    assert all(v['module_id'] is None for v in manifest['labels'])
    assert manifest['geometries'][0]['polygon_px'][0] == (580., 40.)
    assert manifest['geometries'][0]['box_xyxy'] == (580., 40., 640., 120.)
    index = learning.learning_index(result)
    assert index[0]['source_window'] == [20, 20, 760, 560]
    assert index[0]['geometry_coordinate_frame'] == 'source_window'
    assert len({r['split'] for r in index}) == 1
    assert len({r['inspection_group_id'] for r in index}) == 1
    assert all(manifest[k] is False for k in learning.FALSE_FLAGS)
    reopened = comparison.open_partial_comparison(source)
    stored = learning.read_learning_preparation(reopened, key)
    assert stored['current'] and stored['entry']['snapshot_id'] == result['snapshot_id']
    assert stored['entry']['manifest']['geometries'][0]['polygon_px'][0] == [580., 40.]
    assert all(p.read_bytes() == data for p, data in originals.items())
    assert not list(value.folder.glob('*.next.json'))


@pytest.mark.parametrize('failure', ['pending', 'no_positive', 'incomplete', 'reviewer', 'group', 'overlap', 'tiny_overlap', 'boundary'])
def test_incomplete_or_invalid_annotations_cannot_replace_previous_preparation(module_scene, failure):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    before = (value.folder / learning.STATE).read_bytes()
    if failure == 'pending':
        region['entries'][0]['status'] = 'pending'
    elif failure == 'no_positive':
        for entry in region['entries']:
            entry['status'] = 'rejected'
    elif failure in ('overlap', 'tiny_overlap'):
        poly = region['entries'][0]['proposal']['rgb_polygon_px']
        xs, ys = zip(*poly)
        cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
        scale = .1 if failure == 'tiny_overlap' else .5
        child = tuple((cx+(x-cx)*scale, cy+(y-cy)*scale) for x, y in poly)
        region = pv.manual_module_outline(value, region, child)
        region['entries'][-1]['status'] = 'outline_ok'
    elif failure == 'boundary':
        region = pv.manual_module_outline(value, region, ((20, 40), (50, 40), (50, 70), (20, 70)))
        region['entries'][-1]['status'] = 'outline_ok'
    pv.save_module_review(value, {key: region}, key)
    options = dict(reviewer='Synthetic', group_id='Synthetic plant A', complete_annotation=True,
        expected_review_sha256=learning.read_learning_preparation(value, key)['review_sha256'])
    if failure == 'incomplete': options['complete_annotation'] = False
    if failure == 'reviewer': options['reviewer'] = ''
    if failure == 'group': options['group_id'] = 'Another plant'
    with pytest.raises(ValueError):
        learning.save_learning_preparation(value, key, **options)
    assert (value.folder / learning.STATE).read_bytes() == before


def test_overlap_windows_share_group_split_and_later_review_invalidates_only_its_preparation(module_scene):
    _, value = module_scene
    ka, a = reviewed(value)
    kb, b = reviewed(value, (0, 0, 800, 600))
    pv.save_module_review(value, {ka: a, kb: b}, ka)
    first, second = save(value, ka), save(value, kb)
    assert learning.prepared_split(first) == learning.prepared_split(second)
    # No hash partition by individual ROI/module IDs.
    assert learning.learning_index(first)[0]['inspection_group_id'] == learning.learning_index(second)[0]['inspection_group_id']
    a['entries'][0]['note'] = 'Synthetic re-review'
    pv.save_module_review(value, {ka: a, kb: b}, ka)
    assert not learning.read_learning_preparation(value, ka)['current']
    assert learning.read_learning_preparation(value, kb)['current']
    renewed = save(value, ka)
    assert learning.read_learning_preparation(value, ka)['current']
    assert renewed['review_sha256'] != first['review_sha256']


@pytest.mark.parametrize('failure', ['abort', 'review_change', 'concurrent_save'])
def test_abort_or_changes_during_save_preserve_existing_data(module_scene, failure):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    target = value.folder / learning.STATE
    before = target.read_bytes()
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        if calls == 2:
            if failure == 'abort': return True
            if failure == 'review_change':
                region['entries'][0]['note'] = 'Synthetic concurrent change'
                pv.save_module_review(value, {key: region}, key)
            if failure == 'concurrent_save': target.write_bytes(before + b'\n')
        return False
    with pytest.raises((ValueError, RuntimeError)):
        save(value, key, should_cancel=cancel)
    assert target.read_bytes() == before + (b'\n' if failure == 'concurrent_save' else b'')
    assert not list(value.folder.glob('*.next.json'))
    # Explicit continuation from a fresh review state, not a damaged old file.
    save(value, key)
    assert learning.read_learning_preparation(value, key)['current']


def test_dialog_open_revision_is_required_and_tampered_snapshot_or_flags_rejected(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    opened_hash = learning.read_learning_preparation(value, key)['review_sha256']
    region['entries'][0]['note'] = 'Synthetic later edit'
    pv.save_module_review(value, {key: region}, key)
    with pytest.raises(ValueError, match='geändert'):
        learning.save_learning_preparation(value, key, reviewer='Synthetic', group_id='Synthetic',
            complete_annotation=True, expected_review_sha256=opened_hash)
    assert not (value.folder / learning.STATE).exists()
    save(value, key)
    path = value.folder / learning.STATE
    record = json.loads(path.read_text(encoding='utf-8'))
    for changed in (dict(record, training_started=True), deepcopy(record)):
        if not changed['training_started']:
            changed['regions'][key]['manifest']['geometries'][0]['polygon_px'][0][0] += 1
        path.write_text(json.dumps(changed), encoding='utf-8')
        with pytest.raises(ValueError): learning.read_learning_preparation(value, key)


def test_same_plant_group_is_normalized_and_independent_of_roi_and_source_names():
    from mcm_solarcheck.review.training_split import split_for_group
    a = learning.normalize_group('  Anlage  A ')
    b = learning.normalize_group('anlage a')
    assert a == b
    assert split_for_group('pv-site:' + a) == split_for_group('pv-site:' + b)


def test_withdrawal_keeps_other_regions_and_module_reviews_and_can_resume(module_scene):
    _, value = module_scene
    ka, a = reviewed(value)
    kb, b = reviewed(value, (0, 0, 800, 600))
    pv.save_module_review(value, {ka: a, kb: b}, ka)
    save(value, ka)
    save(value, kb)
    module_bytes = (value.folder / pv.STATE).read_bytes()
    opened = learning.read_learning_preparation(value, ka)
    learning.revoke_learning_preparation(value, ka, expected_review_sha256=opened['review_sha256'])
    assert learning.read_learning_preparation(value, ka)['entry'] is None
    assert learning.read_learning_preparation(value, kb)['current']
    second = learning.read_learning_preparation(value, kb)
    learning.revoke_learning_preparation(value, kb, expected_review_sha256=second['review_sha256'])
    assert not learning.read_learning_preparation(value, kb)['current']
    assert learning.read_learning_preparation(value, ka)['group_id'] == 'synthetic plant a'
    save(value, ka)
    assert learning.read_learning_preparation(value, ka)['current']
    assert (value.folder / pv.STATE).read_bytes() == module_bytes


def test_changed_raster_cannot_reuse_annotation_confirmation(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    before = (value.folder / learning.STATE).read_bytes()
    with rasterio.open(value.rgb_path, 'r+') as raster:
        raster.update_tags(SYNTHETIC_CHANGED='true')
    with pytest.raises(ValueError):
        learning.read_learning_preparation(value, key)
    assert (value.folder / learning.STATE).read_bytes() == before


def test_nodata_in_complete_window_blocks_preparation_without_new_files(module_scene):
    source, old = module_scene
    with rasterio.open(old.rgb_path, 'r+') as raster:
        raster.nodata = 0
        values = raster.read(1)
        values[30, 30] = 0
        raster.write(values, 1)
    value = comparison.open_partial_comparison(source, old.rgb_path)
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='looks_aligned', note='Synthetic')
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    with pytest.raises(ValueError, match='ungültige RGB'):
        save(value, key)
    assert not (value.folder / learning.STATE).exists()
