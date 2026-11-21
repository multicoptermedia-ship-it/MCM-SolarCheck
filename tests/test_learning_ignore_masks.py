"""Unseen corners are ignored loss pixels, never guessed PV or background."""
import json
import numpy as np
import pytest
import rasterio

from mcm_solarcheck.services import thermal_partial_pv as pv
from mcm_solarcheck.services import thermal_partial_training as learning
from mcm_solarcheck.services import thermal_partial_comparison as comparison
from test_thermal_partial_training import reviewed, save
from test_thermal_partial_pv import module_scene
from test_thermal_partial_comparison import scene
from test_opensfm_sparse_bridge import sparse_source


def area_for(region, index=0, margin=4):
    col, row, width, height = region['window']
    polygon = np.asarray(region['entries'][index]['proposal']['rgb_polygon_px']) - (col, row)
    left, top = np.maximum((0, 0), polygon.min(axis=0)-margin)
    right, bottom = np.minimum((width-1, height-1), polygon.max(axis=0)+margin)
    return ((float(left), float(top)), (float(right), float(top)),
            (float(right), float(bottom)), (float(left), float(bottom)))


def center(region, index):
    col, row = region['window'][:2]
    x, y = np.mean(region['entries'][index]['proposal']['rgb_polygon_px'], axis=0) - (col, row)
    return round(y), round(x)


def test_unclear_pending_module_is_ignored_while_good_module_and_sources_survive(module_scene):
    source, value = module_scene
    key, region = reviewed(value)
    region['entries'][0]['status'] = 'pending'
    pv.save_module_review(value, {key: region}, key)
    originals = {p: p.read_bytes() for p in (source/'job.json', value.rgb_path, value.thermal_path, value.folder/pv.STATE)}
    entry = save(value, key, ignore_areas=[area_for(region)])
    assert len(entry['manifest']['labels']) == 1
    assert entry['manifest']['ignored_draft_ids'] == [region['entries'][0]['module_id']]
    target = learning.learning_target(entry)
    assert target[center(region, 0)] == 255
    assert target[center(region, 1)] == 1
    assert target[10, 10] == 0
    assert set(np.unique(target)) == {0, 1, 255}
    assert learning.learning_index(entry)[0]['ignore_value'] == 255
    state = learning.read_learning_preparation(value, key)
    assert state['current'] and state['ignored_count'] == 1 and state['module_count'] == 1
    assert all(p.read_bytes() == data for p, data in originals.items())


def test_partial_region_and_nested_fragment_exclude_whole_module_not_only_corner(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    polygon = np.asarray(region['entries'][0]['proposal']['rgb_polygon_px'])
    middle = polygon.mean(axis=0)
    child = tuple(tuple(float(v) for v in middle + (p-middle)*.1) for p in polygon)
    region = pv.manual_module_outline(value, region, child)
    region['entries'][-1]['status'] = 'pending'
    pv.save_module_review(value, {key: region}, key)
    area = area_for(region, len(region['entries'])-1, margin=0)
    entry = save(value, key, ignore_areas=[area])
    assert len(entry['manifest']['ignored_draft_ids']) == 2
    assert len(entry['manifest']['labels']) == 1
    target = learning.learning_target(entry)
    col, row = region['window'][:2]
    x, y = polygon.min(axis=0) - (col, row) + (4, 4)
    assert target[round(y), round(x)] == 255  # Far beyond the tiny explicitly drawn child.
    assert target[center(region, 1)] == 1


def test_unclear_border_draft_can_be_excluded_without_inventing_visible_corners(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    region = pv.manual_module_outline(value, region, ((20, 40), (50, 40), (50, 70), (20, 70)))
    pv.save_module_review(value, {key: region}, key)
    entry = save(value, key, ignore_areas=[((0, 18), (35, 18), (35, 55), (0, 55))])
    assert len(entry['manifest']['labels']) == 2
    assert learning.learning_target(entry)[30, 0] == 255


def test_small_ignore_areas_survive_downsampling_and_counts_share_no_private_fields(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    entry = save(value, key, ignore_areas=[((300, 100), (301, 100), (301, 101), (300, 101))])
    assert np.any(learning.learning_target(entry, (48, 32)) == 255)
    counts = learning.learning_counts(entry)
    assert sum(counts['candidate_480x270_pixels'].values()) == 480*270
    assert counts['ignored_areas'] == 1 and counts['module_outlines'] == 2
    assert counts['original_cvut_profile_verified'] is False
    assert all(counts[k] is False for k in learning.FALSE_FLAGS)
    encoded = json.dumps(counts)
    for private in (str(value.rgb_path), str(value.thermal_path), 'Synthetic reviewer', 'synthetic plant a', region['entries'][0]['module_id']):
        assert private not in encoded


def test_exclusion_edits_change_snapshot_and_roundtrip_without_changing_reviews(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    before = (value.folder/pv.STATE).read_bytes()
    clear = save(value, key)
    ignored = save(value, key, ignore_areas=[area_for(region)])
    assert clear['snapshot_id'] != ignored['snapshot_id']
    state = learning.read_learning_preparation(value, key)
    assert state['current'] and len(state['ignore_areas']) == 1
    restored = save(value, key)
    assert restored['snapshot_id'] == clear['snapshot_id']
    assert (value.folder/pv.STATE).read_bytes() == before


@pytest.mark.parametrize('areas', [
    [[(-1, 0), (10, 0), (10, 10), (0, 10)]],
    [[(0, 0), (10, 10), (0, 10), (10, 0)]],
    [[(0, 0), (0, 0), (0, 0), (0, 0)]],
    [[(0, 0), (float('nan'), 0), (10, 10), (0, 10)]],
    [[(0, 0), (10, 0), (10, 10)]],
    [((0, 0), (2, 0), (2, 2), (0, 2))]*21,
    [((0, 0), (759, 0), (759, 559), (0, 559))],  # No positive/background targets remain.
])
def test_invalid_or_total_exclusion_never_replaces_saved_learning_state(module_scene, areas):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    before = (value.folder/learning.STATE).read_bytes()
    with pytest.raises(ValueError): save(value, key, ignore_areas=areas)
    assert (value.folder/learning.STATE).read_bytes() == before


def test_legacy_preparation_is_readable_but_needs_explicit_new_mask_review(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    path = value.folder/learning.STATE
    record = json.loads(path.read_text(encoding='utf-8'))
    record['check'] = learning.LEGACY_CHECK
    entry = record['regions'][key]
    for field in ('mask_policy', 'user_ignore_polygons_px', 'ignore_polygons_px', 'ignored_draft_ids'):
        del entry['manifest'][field]
    entry['snapshot_id'] = learning._digest(entry['manifest'])
    path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
    before = path.read_bytes()
    assert value.label.encode('utf-8') in before
    state = learning.read_learning_preparation(value, key)
    assert state['current'] and state['needs_mask_review']
    with pytest.raises(ValueError, match='Ältere Vorbereitung'):
        learning.learning_target(state['entry'])
    assert path.read_bytes() == before
    save(value, key, ignore_areas=[area_for(region)])
    assert json.loads(path.read_text(encoding='utf-8'))['check'] == learning.CHECK
    assert not learning.read_learning_preparation(value, key)['needs_mask_review']


def test_nodata_may_only_be_present_inside_explicit_ignore_mask(module_scene):
    source, old = module_scene
    with rasterio.open(old.rgb_path, 'r+') as rgb:
        rgb.nodata = 0
        pixels = rgb.read(1)
        pixels[30, 30] = 0
        rgb.write(pixels, 1)
    value = comparison.open_partial_comparison(source, old.rgb_path)
    comparison.save_partial_comparison(value, opacity=50, zoom=1, verdict='looks_aligned', note='Synthetic')
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    entry = save(value, key, ignore_areas=[((8, 8), (12, 8), (12, 12), (8, 12))])
    assert learning.learning_target(entry)[10, 10] == 255


def test_abort_while_saving_exclusions_keeps_old_masks_and_no_temporary_file(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    save(value, key)
    before = (value.folder/learning.STATE).read_bytes()
    calls = 0
    def cancelled():
        nonlocal calls
        calls += 1
        return calls == 2
    with pytest.raises(RuntimeError): save(value, key, ignore_areas=[area_for(region)], should_cancel=cancelled)
    assert (value.folder/learning.STATE).read_bytes() == before
    assert not list(value.folder.glob('*.next.json'))
    assert learning.read_learning_preparation(value, key)['ignored_count'] == 0


def test_unicode_group_reviewer_and_incomplete_label_roundtrip_in_utf8(module_scene):
    _, value = module_scene
    key, region = reviewed(value)
    pv.save_module_review(value, {key: region}, key)
    learning.save_learning_preparation(value, key, reviewer='Prüferin Änne', group_id='Anlage ÜBERDACHUNG',
        complete_annotation=True, ignore_areas=[area_for(region)],
        expected_review_sha256=learning.read_learning_preparation(value, key)['review_sha256'])
    stored = learning.read_learning_preparation(value, key)
    assert stored['current']
    assert stored['group_id'] == 'anlage überdachung'
    assert stored['entry']['reviewer'] == 'Prüferin Änne'
    assert value.label.encode('utf-8') in (value.folder/learning.STATE).read_bytes()
