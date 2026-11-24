"""Actual full external U-Net training and reload; generated samples only."""
import json
import os

import pytest

from mcm_solarcheck.services import pv_synthetic_training as probe
from test_cvut_cpu_runtime import runtime

pytestmark = pytest.mark.skipif(not os.environ.get('SOLARCHECK_TEST_CVUT_RUNTIME'),
    reason='Explicit isolated Torch CPU qualification only')


@pytest.fixture(scope='module')
def trained(runtime):
    torch, root, spec = runtime
    # Deliberately invalid published-weight sentinel: this probe must never load it.
    source = root/spec['weights']
    source.write_bytes(b'original published-weight location must remain unread/unmodified')
    before = {p: p.read_bytes() for p in (root/'vendor').rglob('*') if p.is_file()}
    before[source] = source.read_bytes()
    result = probe.run_probe(root)
    assert all(p.read_bytes() == data for p, data in before.items())
    return root, result


def test_full_reference_really_updates_parameters_and_reloads_exact_outputs(trained):
    root, result = trained
    assert result['status'] == 'passed' and result['changed_parameter_tensors'] == 64
    assert result['ignore_gradient_verified'] and result['reload_verified']
    assert result['weights_bytes'] > 120_000_000
    assert result['synthetic_losses'][-1] < result['synthetic_losses'][0]
    assert all(result[k] is False for k in probe.FALSE_FLAGS)
    assert probe.read_probe(root) == result
    assert str(root) not in json.dumps(result)


@pytest.mark.parametrize('cancel_at', [3, 8])
def test_cancel_during_training_or_after_reload_preserves_previous_completed_probe(trained, cancel_at):
    root, previous = trained
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        return calls == cancel_at
    with pytest.raises(RuntimeError):
        probe.run_probe(root, should_cancel=cancel)
    assert probe.read_probe(root) == previous
    assert not list((root/probe.FOLDER).glob('*.next'))


def test_changed_external_reference_cannot_publish_new_training_probe(trained):
    root, previous = trained
    path = root/'vendor/unet/unet_model.py'
    before = path.read_bytes()
    try:
        path.write_bytes(b'changed')
        with pytest.raises(ValueError):
            probe.run_probe(root)
    finally:
        path.write_bytes(before)
    assert probe.read_probe(root) == previous
    assert not list((root/probe.FOLDER).glob('*.next'))
