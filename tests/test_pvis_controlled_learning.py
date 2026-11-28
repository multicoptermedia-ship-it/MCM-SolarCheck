"""Generated public-corpus/learning contracts; no Torch, private pixels or network."""
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from mcm_solarcheck.services import pvis_learning_corpus as corpus
from mcm_solarcheck.services import pvis_controlled_learning as learning
from test_pvis_public_training import pilot
from test_pvis_image_adapter import public_pixels
from test_pvis_public_reference import reference

cli = importlib.import_module('MCM_SolarCheck_PVIS_LERNEN')


def generated_corpus(root):
    config = dict(generator='synthetic_unit_data')
    folder = root/corpus.fingerprint(config); folder.mkdir(parents=True)
    rows = []
    for i, split in enumerate(('train', 'train', 'validation', 'validation')):
        rgb = np.zeros((64, 64, 3), np.uint8); target = np.zeros((64, 64), np.int32)
        target[8:32, 8:24] = 1
        if i: target[8:32, 24:40] = 2
        target[1:4] = -1; rgb[target > 0] = (80, 100, 150)
        name = sha256(str(i).encode()).hexdigest()
        rows.append(dict(corpus_id=folder.name, sample_id=name, station='009' if split == 'train' else '033',
            split=split, instances=len(np.unique(target[target > 0])), source_record_sha256='a'*64,
            data_sha256=corpus.write_crop(folder, name, rgb, target)))
    manifest = corpus.seal(dict(check=corpus.CHECK, corpus_id=folder.name, config=config, size=64,
        samples=rows, split_counts=dict(train=2, validation=2), synthetic_only=True,
        source_url=corpus.SOURCE, profile=corpus.PROFILE, label_policy='pvis-projected-whole-module-1',
        license_declared='CC-BY-4.0', license_decision='unreviewed', commercial_training_approved=False,
        test_images=0, customer_images=0))
    (folder/'corpus.json').write_text(json.dumps(manifest))
    return folder, manifest


def test_generated_numeric_corpus_retains_instances_and_requires_explicit_synthetic_mode(tmp_path):
    folder, manifest = generated_corpus(tmp_path)
    rgb, target = corpus.read_corpus(folder, manifest, synthetic=True)
    assert rgb.shape == (4, 64, 64, 3) and set(np.unique(target)) == {-1, 0, 1, 2}
    with pytest.raises(ValueError): corpus.read_corpus(folder, manifest)


@pytest.mark.parametrize('field,value', [('test_images', 1), ('customer_images', 1), ('size', 512),
    ('license_decision', 'approved'), ('commercial_training_approved', True), ('label_policy', 'visible-only')])
def test_resealed_corpus_cannot_change_public_scope(tmp_path, field, value):
    _, manifest = generated_corpus(tmp_path); manifest[field] = value
    with pytest.raises(ValueError): corpus.validate(corpus.seal(manifest), synthetic=True)


@pytest.mark.parametrize('kind', ['duplicate', 'test-role', 'source-hash', 'data', 'members', 'pickle'])
def test_numeric_corpus_tamper_and_test_station_are_rejected(tmp_path, kind):
    folder, manifest = generated_corpus(tmp_path)
    if kind == 'duplicate': manifest['samples'][1] = dict(manifest['samples'][0])
    if kind == 'test-role': manifest['samples'][0].update(station='024', split='test')
    if kind == 'source-hash': manifest['samples'][0]['source_record_sha256'] = 'changed'
    if kind == 'data': (folder/(manifest['samples'][0]['sample_id']+'.npz')).write_bytes(b'changed')
    if kind == 'members':
        p = folder/(manifest['samples'][0]['sample_id']+'.npz'); np.savez(p, rgb=np.zeros(1), unexpected=np.zeros(1))
        manifest['samples'][0]['data_sha256'] = sha256(p.read_bytes()).hexdigest()
    if kind == 'pickle':
        p = folder/(manifest['samples'][0]['sample_id']+'.npz')
        np.savez(p, rgb=np.array([object()], dtype=object), instances=np.zeros((64, 64), np.int32))
        manifest['samples'][0]['data_sha256'] = sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError): corpus.read_corpus(folder, corpus.seal(manifest), synthetic=True)


def test_balanced_order_covers_every_source_and_repeats_only_smaller_stratum():
    rows = [dict(split='train', instances=x) for x in (1, 1, 1, 2, 3)]
    rows.append(dict(split='validation', instances=2))
    sequence = learning.order(rows, 0)
    assert len(sequence) == 6 and set(sequence) == set(range(5)) and 5 not in sequence
    assert all(rows[i]['instances'] == 1 for i in sequence[::2])
    assert all(rows[i]['instances'] > 1 for i in sequence[1::2])
    assert learning.order(rows, 0) == sequence


def test_augmentation_preserves_exact_unknown_and_instance_pixels():
    rgb = np.zeros((64, 64, 3), np.uint8); target = np.zeros((64, 64), np.int32)
    target[3:20, 5:9] = 2; target[9:12] = -1; rgb[:, :, 0] = (target > 0)*200
    for step in range(8):
        image, transformed = learning.augment(rgb, target, step)
        assert np.array_equal(image[:, :, 0] > 0, transformed > 0)
        assert np.unique(target, return_counts=True)[1].tolist() == np.unique(transformed, return_counts=True)[1].tolist()
        assert image.flags.c_contiguous and transformed.flags.c_contiguous


def test_both_balanced_strata_receive_all_eight_geometric_variants():
    target = np.arange(64*64, dtype=np.int32).reshape(64, 64)
    image = np.zeros((64, 64, 3), np.uint8)
    variants = [{learning.augment(image, target, step)[1].tobytes() for step in range(parity, 16, 2)}
                for parity in (0, 1)]
    assert len(variants[0]) == len(variants[1]) == 8 and variants[0] == variants[1]


def test_incomplete_validation_cannot_win_using_only_partial_subset_f1():
    target = np.zeros((64, 64), np.int32); target[8:32, 8:32] = 1
    raw = target > 0
    incomplete = learning._metrics([target], [raw], [target], [dict(status='limit_exceeded_unscored')])
    complete_empty = learning._metrics([target], [np.zeros_like(raw)], [np.zeros_like(target)], [dict(status='complete')])
    assert complete_empty['selection_rank'] > incomplete['selection_rank']


def test_corpus_preparation_cancel_resume_preserves_old_audit(public_pixels, tmp_path):
    _, source = public_pixels; audit = pilot.audited; audit.audit(source)
    before = (source/'image-adapter.json').read_bytes()
    output = tmp_path/'new-corpus'
    with pytest.raises(KeyboardInterrupt):
        corpus.prepare(source, output, audit, synthetic=True,
            should_cancel=lambda: bool(list(output.glob('*/*.npz'))))
    folder, manifest = corpus.prepare(source, output, audit, synthetic=True)
    assert manifest['split_counts'] == dict(train=2, validation=1)
    assert (source/'image-adapter.json').read_bytes() == before
    assert corpus.prepare(source, output, audit, synthetic=True) == (folder, manifest)


def test_learning_root_does_not_adopt_old_pilot_or_unowned_files(tmp_path):
    root = pilot._root(tmp_path/'old-pilot')
    with pytest.raises(ValueError): cli.root_folder(root)
    assert cli.root_folder(tmp_path/'new') == tmp_path/'new'


def test_cli_mode_and_session_limits_are_explicit_and_errors_do_not_expose_paths(tmp_path, capsys):
    for args in ([], ['--learn-public', '--session-minutes', '21']):
        with pytest.raises(SystemExit): cli.main(args)
    imported = 'torch' in sys.modules
    assert cli.main(['--show', '--prefix', str(tmp_path), '--parent-prefix', str(tmp_path/'missing')]) == 2
    report = json.loads(capsys.readouterr().out)
    assert str(tmp_path) not in json.dumps(report) and report['model_updated'] is False
    assert ('torch' in sys.modules) == imported


def test_public_parameters_cannot_be_overridden(tmp_path):
    _, manifest = generated_corpus(tmp_path)
    parent = dict(run_id='a'*64, report_sha256='b'*64, weights_sha256='c'*64)
    with pytest.raises(ValueError): learning.identity(manifest, parent, {}, parameters=dict(epochs=1000))


@pytest.mark.parametrize('name', ['../other.pt', 'checkpoint-00000000.pt', 'EXPERIMENTAL-CANDIDATE-1.pt'])
def test_candidate_names_cannot_escape_or_load_other_weights(tmp_path, name):
    with pytest.raises(ValueError): learning._candidate(tmp_path, name, 'a'*64)


def test_candidate_hash_and_signed_metadata_tamper_rejected(tmp_path):
    p = tmp_path/'EXPERIMENTAL-CANDIDATE-00000000.pt'; p.write_bytes(b'generated fixture bytes')
    with pytest.raises(ValueError): learning._candidate(tmp_path, p.name, 'a'*64)
    record = learning.sealed(dict(saved_steps=10)); record['saved_steps'] = 20
    path = tmp_path/'metadata.json'; path.write_text(json.dumps(record))
    with pytest.raises(ValueError): learning.read_json(path)


def test_changed_source_or_parent_cannot_silently_start_a_new_run_in_same_root(tmp_path, monkeypatch):
    root = cli.root_folder(tmp_path/'learning'); parent_root = tmp_path/'old'; parent_root.mkdir()
    folder, manifest = generated_corpus(root/'corpora'); parent_job = parent_root/('b'*64)
    monkeypatch.setattr(cli, '_input', lambda *a: (None, None, parent_job))
    parent = dict(run_id=parent_job.name, report_sha256='c'*64, weights_sha256='d'*64)
    monkeypatch.setattr(learning, '_parent', lambda *a: parent)
    monkeypatch.setattr(learning, 'run', lambda *a, **k: pytest.fail('Changed lineage started training'))
    (root/'active.json').write_text(json.dumps(dict(corpus_id=folder.name, run_id='a'*64, parent_run_id=parent_job.name)))
    with pytest.raises(ValueError): cli.worker(root, parent_root, tmp_path/'reference', folder.name, 20)
