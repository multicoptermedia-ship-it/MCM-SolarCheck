"""Real pinned CPU U-Net instance training, generated arrays only; opt-in."""
import json
import os
import shutil

import pytest

from mcm_solarcheck.services import pvis_instance_training as trainer
from mcm_solarcheck.services import pvis_public_training_data as data
from test_cvut_cpu_runtime import runtime
from test_pvis_public_training import numeric_package

pytestmark = pytest.mark.skipif(not os.environ.get('SOLARCHECK_TEST_CVUT_RUNTIME'),
    reason='Explicit isolated Torch CPU qualification only')


def test_instance_loss_is_permutation_invariant_separates_modules_and_masks_all_gradients(runtime):
    torch, _, _ = runtime
    torch.manual_seed(7)
    logits = torch.randn(1, 4, 8, 8, requires_grad=True)
    target = torch.zeros(1, 8, 8, dtype=torch.long)
    target[:, 1:4, 1:4] = 2; target[:, 1:4, 4:7] = 5; target[:, 6:] = -1
    loss, parts = trainer.instance_loss(torch, logits, target)
    renamed = torch.where(target == 2, 90, torch.where(target == 5, 3, target))
    assert torch.allclose(loss, trainer.instance_loss(torch, logits, renamed)[0])
    assert parts['distance'] > 0
    loss.backward()
    assert torch.all(logits.grad[:, :, 6:] == 0)
    assert torch.any(logits.grad[:, 2:, 1:4] != 0)
    altered = logits.detach().clone(); altered[:, :, 6:] = 999
    assert torch.allclose(loss, trainer.instance_loss(torch, altered, target)[0])
    all_unknown = torch.full_like(target, -1)
    with pytest.raises(ValueError): trainer.instance_loss(torch, logits, all_unknown)


def test_full_reference_epoch_resume_equals_uninterrupted_training_and_reopens(runtime, tmp_path, monkeypatch):
    torch, reference, spec = runtime
    package, manifest = numeric_package(tmp_path/'package')
    params = dict(trainer.PARAMETERS, epochs=2)
    # No published weights may be read/changed; checked vendor code remains intact.
    sentinel = reference/spec['weights']; sentinel.write_bytes(b'never load published weights')
    source_before = {p: p.read_bytes() for p in (reference/'vendor').rglob('*') if p.is_file()}
    previous = tmp_path/'previous-model'; previous.write_bytes(b'keep existing recognizer')
    cancelled = tmp_path/'resumed'
    try:
        with pytest.raises(KeyboardInterrupt):
            trainer.run_training(package, manifest, reference, cancelled, allow_synthetic=True, parameters=params,
                should_cancel=lambda: bool(list(cancelled.glob('*/progress.json'))))
        checkpoint = next(cancelled.glob('*/epoch-001.pt'))
        assert checkpoint.is_file() and not list(cancelled.glob('*/report.json'))
        saved_progress = next(cancelled.glob('*/progress.json'))
        original_progress = saved_progress.read_bytes()
        changed_progress = json.loads(original_progress); changed_progress['epoch'] = 2
        saved_progress.write_text(json.dumps(changed_progress))
        with pytest.raises((ValueError, FileNotFoundError)):
            trainer.run_training(package, manifest, reference, cancelled, allow_synthetic=True, parameters=params)
        saved_progress.write_bytes(original_progress)
        resumed = trainer.run_training(package, manifest, reference, cancelled, allow_synthetic=True, parameters=params)
        assert resumed['steps'] == 4 and resumed['changed_parameter_tensors'] >= 60
        assert resumed['ignore_gradient_verified'] and resumed['reload_verified']
        job = cancelled/resumed['run_id']
        assert trainer.read_report(job, resumed['run_id']) == resumed
        assert not list(job.glob('epoch-*.pt')) and not (job/'progress.json').exists()
        # Release the first 124MB weights after exercising reopening/tampering.
        state_hash, history = resumed['final_state_sha256'], resumed['history']
        report_path = job/'report.json'; original_report = report_path.read_bytes()
        altered = json.loads(original_report); altered['final_validation']['loss'] += 1
        report_path.write_text(json.dumps(altered))
        with pytest.raises(ValueError): trainer.read_report(job, resumed['run_id'])
        report_path.write_bytes(original_report)
        with monkeypatch.context() as m:
            m.setattr(trainer, 'reference_model', lambda *a, **k: pytest.fail('Reopen constructed a model'))
            assert trainer.read_report(job, resumed['run_id']) == resumed
        shutil.rmtree(cancelled)
        fresh = trainer.run_training(package, manifest, reference, tmp_path/'fresh',
            allow_synthetic=True, parameters=params)
        assert fresh['final_state_sha256'] == state_hash and fresh['history'] == history
        assert previous.read_bytes() == b'keep existing recognizer'
        assert sentinel.read_bytes() == b'never load published weights'
        assert all(p.read_bytes() == b for p, b in source_before.items())
    finally:
        for folder in (cancelled, tmp_path/'fresh'):
            if folder.exists(): shutil.rmtree(folder)
