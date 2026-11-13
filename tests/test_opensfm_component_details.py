"""Read-only component counts from synthetic saved reconstructions, never photos."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services import opensfm_dense_continuation as resume
from mcm_solarcheck.services.colmap_openmvs_pilot import PilotError
from test_opensfm_thermal_pilot import thermal_inputs, thermal_engine
from test_opensfm_rgb_pilot import reconstruction, metric_path


def split_models(names):
    result = reconstruction(names[:2]) + reconstruction(names[1:])
    result[0]['points'] = {'shared-track': {}, 'first-only': {}}
    result[1]['points'] = {'shared-track': {}, 'second-only': {}, 'third': {}}
    return result


@pytest.fixture
def stopped_components(tmp_path):
    frames, config = thermal_inputs(tmp_path)
    with pytest.raises(PilotError, match='Kameraverbund'):
        pilot.run_opensfm_thermal_pilot(frames, config, executor=thermal_engine([], model=split_models))
    folder, = config.output_parent.iterdir()
    return folder


def test_new_summary_counts_points_in_all_models_without_accepting_fragmented_geometry(tmp_path):
    path = tmp_path / 'models.json'
    path.write_text(json.dumps(split_models(['000001.JPG', '000002.JPG', '000003.JPG'])))
    result = pilot.reconstruction_summary(path, {'000001.JPG', '000002.JPG', '000003.JPG'})
    assert result['registered_images'] == 3 and result['missing_images'] == 0
    assert result['models'] == 2 and result['points'] == 5 and result['points_scope'] == 'sum_per_model'
    assert result['registration_complete'] is False


def test_reopen_corrects_legacy_zero_counts_and_exports_only_component_sums(stopped_components, monkeypatch):
    folder = stopped_components
    path = metric_path(folder)
    report = json.loads(path.read_text())
    report.update(points=0)  # Exact historical reporting bug with multiple models.
    report.pop('points_scope', None)
    report['reconstruction_details'] = {'PRIVATE FIELD': 'never copy'}
    path.write_text(json.dumps(report))
    before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    monkeypatch.setattr(pilot, '_execute', lambda *a, **k: pytest.fail('No engine'))
    result = resume.read_opensfm_run_metrics(folder)
    assert result['points'] == 5 and result['points_scope'] == 'sum_per_model'
    detail = result['reconstruction_details']
    assert detail['status'] == 'completed' and not detail['geometric_quality_verified']
    assert detail['components'] == [dict(model_index=0, images=2, point_records=2, cameras=1),
                                    dict(model_index=1, images=2, point_records=3, cameras=1)]
    assert detail['pairs'] == [dict(model_a=0, model_b=1, shared_images=1, shared_point_ids=1)]
    assert detail['unique_registered_images'] == 3  # Overlapping models must not sum to four images.
    text = json.dumps(result)
    for forbidden in ('PRIVATE FIELD', str(folder), 'source_file', '000001.JPG', 'shared-track', 'latitude'):
        assert forbidden not in text
    assert not result['registration_complete'] and not result['orthophoto_created']
    assert not resume.can_continue_opensfm(result)
    assert all(p.read_bytes() == content for p, content in before.items())


@pytest.mark.parametrize('bad', ['json', 'mapping', 'mismatch', 'symlink', 'changed'])
def test_changed_or_bad_saved_components_preserve_original_metrics_and_do_not_compute(stopped_components, tmp_path, monkeypatch, bad):
    folder = stopped_components
    path = folder / 'reconstruction.json'
    if bad == 'json':
        path.write_text('not JSON')
    elif bad == 'mapping':
        (folder / 'input-map.json').write_text('[{"working_name":"../outside.JPG"}]')
    elif bad == 'mismatch':
        path.write_text(json.dumps(reconstruction(['999999.JPG'])))
    elif bad == 'symlink':
        outside = tmp_path / 'outside.json'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(outside)
        except OSError:
            pytest.skip('OS cannot create a file symlink')
    elif bad == 'changed':
        read = pilot._json
        def mutate(value):
            result = read(value)
            if Path(value).name == 'input-map.json':
                path.write_text(path.read_text() + ' ')
            return result
        monkeypatch.setattr(pilot, '_json', mutate)
    result = resume.read_opensfm_run_metrics(folder)
    assert result['reconstruction_details']['status'] != 'completed'
    assert result['status'] == 'failed' and result['registration_complete'] is False
    assert not result['orthophoto_created']
