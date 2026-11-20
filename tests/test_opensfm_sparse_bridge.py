"""One native supplement with synthetic saved caches and byte-preserving copies."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from mcm_solarcheck.services import opensfm_rgb_pilot as pilot
from mcm_solarcheck.services import opensfm_sparse_bridge as bridge
from mcm_solarcheck.services.colmap_openmvs_pilot import PilotError, PilotTimeout, ThermalPilotFrame
from test_opensfm_thermal_pilot import thermal_inputs, thermal_engine
from test_opensfm_rgb_pilot import reconstruction


@pytest.fixture
def sparse_source(tmp_path):
    frames, config = thermal_inputs(tmp_path)
    first = Path(frames[0].source_file).read_bytes()
    for index in range(3, 10):
        path = Path(frames[0].source_file).with_name(f'synthetic-extra-{index}.JPG')
        path.write_bytes(first)
        frames.append(ThermalPilotFrame(str(index), str(path), 50, 8, 100, sha256(first).hexdigest()))
    def models(names):
        return reconstruction(names[:8]) + reconstruction(names[8:])
    with pytest.raises(PilotError, match='Kameraverbund'):
        pilot.run_opensfm_thermal_pilot(frames, config, executor=thermal_engine([], model=models))
    source, = config.output_parent.iterdir()
    (source / 'camera_models.json').write_text('synthetic private camera models')
    (source / 'features').mkdir()
    (source / 'matches').mkdir()
    for path in (source / 'images').iterdir():
        (source / 'features' / (path.name + '.features.npz')).write_bytes(b'synthetic private descriptors')
        (source / 'matches' / (path.name + '_matches.pkl.gz')).write_bytes(b'synthetic native matches')
    return source, config


def supplemented_engine(calls, *, failure=None):
    delegate = thermal_engine(calls)
    def execute(executable, args, folder, log, cancel, **kwargs):
        stage = args[args.index('-I') + 2]
        if stage == 'match_missing':
            assert not cancel()
            calls.append(stage)
            assert (folder / 'features/000001.JPG.features.npz').read_bytes() == b'synthetic private descriptors'
            assert (folder / 'matches/000001.JPG_matches.pkl.gz').read_bytes() == b'synthetic native matches'
            assert not (folder / 'reconstruction.json').exists()
            if failure == 'timeout':
                raise PilotTimeout('synthetic')
            if failure == 'mutation':
                source = Path(json.loads((folder / 'job.json').read_text())['bridge_plan']['source_workspace'])
                (source / 'features/000001.JPG.features.npz').write_bytes(b'changed')
            result = dict(status='finished', target_images=2, candidate_pairs=17,
                previous_pairs_skipped=4, new_pairs=13, matched_pairs=0 if failure == 'empty' else 3)
            (folder / 'matching-supplement.json').write_text(json.dumps(result))
            return
        if stage == 'reconstruct' and failure == 'fragmented':
            calls.append(stage)
            names = sorted(p.name for p in (folder / 'images').iterdir())
            (folder / 'reconstruction.json').write_text(json.dumps(reconstruction(names[:8]) + reconstruction(names[8:])))
            return
        delegate(executable, args, folder, log, cancel, **kwargs)
    return execute


def test_once_only_supplement_reuses_caches_preserves_old_files_and_reaches_thermal_geotiff(sparse_source, monkeypatch):
    source, config = sparse_source
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    monkeypatch.setattr(pilot, '_require_thermal_copy', lambda *a: pytest.fail('Do not repeat raw decoding'))
    calls = []
    result = bridge.run_sparse_bridge(source, config, executor=supplemented_engine(calls))
    assert calls == ['match_missing', *pilot.STAGES[3:]]
    assert result.thermal_images == 10 and result.thermal_geotiff.is_file()
    assert source not in result.workspace.parents
    assert all(p.read_bytes() == data for p, data in before.items())
    report = pilot.read_opensfm_metrics(result.workspace)
    assert report['status'] == 'finished' and report['thermal_created'] and report['registration_complete']
    assert report['steps'][0]['reused'] and report['steps'][1]['reused']
    assert report['matching_supplement']['new_pairs'] == 13
    assert report['radiometric_sources_preserved'] == 10 and not report['temperature_verified']
    assert 'target_names' not in json.dumps(report) and str(source) not in json.dumps(report)
    with pytest.raises(PilotError, match='einmal'):
        bridge.run_sparse_bridge(source, config, executor=lambda *a, **k: pytest.fail('No second attempt'))


@pytest.mark.parametrize('failure', ['timeout', 'empty', 'fragmented', 'mutation'])
def test_failed_or_unlinked_attempt_does_not_advance_to_dense(sparse_source, failure):
    source, config = sparse_source
    calls, folders = [], []
    with pytest.raises(PilotError):
        bridge.run_sparse_bridge(source, config, executor=supplemented_engine(calls, failure=failure), on_workspace=folders.append)
    assert not any(stage in calls for stage in pilot.STAGES[5:])
    report = pilot.read_opensfm_metrics(folders[0])
    assert report['status'] == 'failed' and not report['orthophoto_created']
    assert not report['thermal_created'] and not bridge.can_bridge(report)
    if failure == 'empty':
        assert calls == ['match_missing']


def test_changed_working_checksum_is_not_reparsed_or_used_for_matching(sparse_source):
    source, config = sparse_source
    path = source / 'images/000001.JPG'
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(PilotError):
        bridge.run_sparse_bridge(source, config, executor=lambda *a, **k: pytest.fail('No matching'))


def test_nonqualifying_rgb_or_large_fragmentation_is_not_automatically_retried(sparse_source):
    source, config = sparse_source
    report = pilot.read_opensfm_metrics(source)
    assert bridge.can_bridge(report)
    assert not bridge.can_bridge({**report, 'pipeline': 'opensfm_rgb'})
    detail = {**report['reconstruction_details'], 'components': [dict(images=5), dict(images=5)]}
    assert not bridge.can_bridge({**report, 'reconstruction_details': detail})
    assert not bridge.can_bridge({**report, 'matching_supplement': dict(status='finished')})
