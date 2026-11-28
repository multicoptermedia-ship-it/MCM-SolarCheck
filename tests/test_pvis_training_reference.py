"""Generated archive/partition tests only; no dataset download or customer input."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from test_pvis_public_reference import fixture_zip, pv, reference
from mcm_solarcheck.services.pvis_training_reference import (
    LABEL_POLICY, REPORT, annotation_contract, build_partition,
)


@pytest.fixture
def prepared(reference, monkeypatch):
    source, root, stations = reference
    pv.intake(root, source)
    validation = fixture_zip(source, pv.VALIDATION)
    monkeypatch.setattr(pv, 'VALIDATION', validation)
    return source, root, stations, validation


def test_three_stations_and_label_contract_preserve_original_report(prepared):
    source, root, stations, validation = prepared
    original = (root/'reference.json').read_bytes()
    sources = {p.name: p.read_bytes() for p in source.iterdir()}
    result = pv.prepare_splits(root, source)
    assert result['check'] == 'solarcheck-pvis-training-reference-1'
    assert result['images'] == result['annotation_observations'] == 3
    assert result['split_images'] == dict(train=1, validation=1, test=1)
    assert [(r['station'], r['source_split'], r['split']) for r in result['stations']] == [
        ('009', 'train', 'train'), ('033', 'train', 'validation'), ('024', 'test', 'test')]
    partition = result['partition']
    assert partition['model_selection_split'] == 'validation'
    assert partition['test_reserved_for_final_evaluation']
    assert partition['crops_inherit_station_split']
    assert partition['annotation_contract']['id'] == LABEL_POLICY
    assert partition['annotation_contract']['occluded_module_count'] is None
    assert partition['annotation_contract']['visible_corner_labels_compatible'] is False
    assert result['visible_corner_eligibility_verified'] is False
    for field in ('image_decoding_verified', 'physical_module_ids_confirmed',
                  'commercial_training_approved', 'training_authorized', 'training_started',
                  'model_updated', 'customer_images_read', 'images_exported',
                  'accuracy_verified', 'automatically_accepted', 'coverage_verified',
                  'temperature_verified', 'georeferencing_verified', 'production_approved'):
        assert result[field] is False
    assert (root/'reference.json').read_bytes() == original
    assert {p.name: p.read_bytes() for p in source.iterdir()} == sources
    assert pv.intake(root, show=True)['images'] == 2
    for p in source.iterdir(): p.unlink()
    assert pv.prepare_splits(root, show=True) == result
    assert not list(root.rglob('*.jpg'))


def test_base_must_be_verified_before_new_download(prepared, monkeypatch):
    source, root, _, validation = prepared
    saved = json.loads((root/'reference.json').read_text())
    saved['images'] = 9000
    (root/'reference.json').write_text(json.dumps(saved))
    with pytest.raises(ValueError):
        pv.prepare_splits(root, source)
    assert not (root/validation.name).exists()
    assert not (root/REPORT).exists()


def test_interrupted_copy_and_resume_preserve_original_reference(prepared):
    source, root, _, validation = prepared
    before = (root/'reference.json').read_bytes()
    partial = root/(validation.name+'.download')
    with pytest.raises(KeyboardInterrupt):
        pv.prepare_splits(root, source, should_cancel=lambda: partial.exists() and partial.stat().st_size > 0)
    assert not partial.exists() and not (root/REPORT).exists()
    assert (root/'reference.json').read_bytes() == before
    result = pv.prepare_splits(root, source)
    (source/validation.name).unlink()
    assert pv.prepare_splits(root, source) == result


def test_cancel_after_validated_result_preserves_completed_reports(prepared, monkeypatch):
    source, root, _, _ = prepared
    pv.prepare_splits(root, source)
    before = {name: (root/name).read_bytes() for name in ('reference.json', REPORT)}
    real, completed = pv._split_report, []
    def finish(*args):
        report = real(*args)
        completed.append(True)
        return report
    monkeypatch.setattr(pv, '_split_report', finish)
    with pytest.raises(KeyboardInterrupt):
        pv.prepare_splits(root, source, should_cancel=lambda: bool(completed))
    assert {name: (root/name).read_bytes() for name in before} == before


@pytest.mark.parametrize('change', ['role', 'policy', 'digest', 'training_flag', 'source_hash'])
def test_changed_split_or_label_report_cannot_reopen(prepared, change):
    source, root, _, _ = prepared
    pv.prepare_splits(root, source)
    path = root/REPORT
    record = json.loads(path.read_text())
    if change == 'role': record['partition']['stations'][2]['split'] = 'train'
    elif change == 'policy': record['partition']['annotation_contract']['target'] = 'visible_only'
    elif change == 'digest': record['partition_sha256'] = '0'*64
    elif change == 'training_flag': record['training_started'] = True
    elif change == 'source_hash': record['base_reference_sha256'] = '1'*64
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        pv.prepare_splits(root, show=True)
    assert pv.intake(root, show=True)['images'] == 2


def test_validation_corruption_blocks_only_new_reference(prepared):
    source, root, _, validation = prepared
    pv.prepare_splits(root, source)
    before = (root/REPORT).read_bytes()
    path = root/validation.name
    content = path.read_bytes()
    path.write_bytes(content[:-1]+bytes([content[-1] ^ 1]))
    with pytest.raises(ValueError): pv.prepare_splits(root, show=True)
    assert (root/REPORT).read_bytes() == before
    assert pv.intake(root, show=True)['images'] == 2


def test_partial_from_killed_process_is_removed_before_space_check(prepared, monkeypatch):
    source, root, _, validation = prepared
    partial = root/(validation.name+'.download')
    partial.write_bytes(b'own-interrupted-public-download')
    monkeypatch.setattr(pv.shutil, 'disk_usage', lambda _: SimpleNamespace(
        free=0 if partial.exists() else validation.size + 50_000_000))
    assert pv.prepare_splits(root, source)['validation_stations'] == 1
    assert not partial.exists()


def test_original_report_survives_insufficient_space(prepared, monkeypatch):
    source, root, _, validation = prepared
    before = (root/'reference.json').read_bytes()
    monkeypatch.setattr(pv.shutil, 'disk_usage', lambda _: SimpleNamespace(free=0))
    with pytest.raises(OSError) as error: pv.prepare_splits(root, source)
    assert error.value.errno == 28
    assert (root/'reference.json').read_bytes() == before
    assert not (root/validation.name).exists()


def test_new_and_original_commands_share_process_lock(prepared):
    _, root, _, _ = prepared
    with pv.package_lock(root, 'pvis-package.lock'):
        child = subprocess.run([sys.executable, str(Path(pv.__file__)), '--prefix', str(root),
                                '--prepare-splits'], capture_output=True, text=True, timeout=15)
    assert child.returncode == 2
    assert json.loads(child.stdout)['error_code'] == 'LOCAL_IO'


def test_cli_reopens_without_source_or_network(prepared, capsys):
    source, root, _, _ = prepared
    pv.prepare_splits(root, source)
    assert pv.main(['--prefix', str(root), '--show-splits']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['validation_stations'] == 1
    assert str(root) not in json.dumps(report)


def test_station_order_cannot_change_partition_identity(prepared):
    source, root, _, _ = prepared
    pv.prepare_splits(root, source)
    rows = [*pv.intake(root, show=True)['stations'], pv.inspect_station(root/pv.VALIDATION.name, pv.VALIDATION)]
    assert build_partition(rows) == build_partition(rows[::-1])


@pytest.mark.parametrize('case', ['duplicate', 'test_to_train', 'validation_from_test', 'unknown', 'missing'])
def test_partition_rejects_site_leakage_or_changed_upstream_split(prepared, case):
    source, root, _, _ = prepared
    rows = [*pv.intake(root, show=True)['stations'], pv.inspect_station(source/pv.VALIDATION.name, pv.VALIDATION)]
    if case == 'duplicate': rows[2] = deepcopy(rows[0])
    elif case == 'test_to_train': rows[1]['split'] = 'train'
    elif case == 'validation_from_test': rows[2]['split'] = 'test'
    elif case == 'unknown': rows[2]['station'] = '999'
    elif case == 'missing': rows.pop()
    with pytest.raises(ValueError): build_partition(rows)


def test_projected_annotations_rejected_by_visible_corner_training_path(prepared):
    from mcm_solarcheck.services.thermal_partial_training import AREA_MASK_POLICY, learning_target
    assert annotation_contract()['target'] == 'whole_module_projected_including_occluded_parts'
    with pytest.raises(ValueError): annotation_contract(AREA_MASK_POLICY)
    with pytest.raises(ValueError): learning_target({'manifest': {'mask_policy': LABEL_POLICY}})


def test_fixed_validation_archive_is_from_upstream_train():
    assert (pv.VALIDATION.station, pv.VALIDATION.split, pv.VALIDATION.images,
            pv.VALIDATION.annotations, pv.VALIDATION.size) == ('033', 'train', 142, 18675, 392372468)
    assert sum(s.images for s in (*pv.STATIONS, pv.VALIDATION)) == 284
