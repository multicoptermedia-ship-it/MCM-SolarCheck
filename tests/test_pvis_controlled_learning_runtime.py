"""Real full external U-Net / Adam / RNG cursor resume on generated64px crops."""
import os
import shutil

import pytest

from mcm_solarcheck.services import pvis_instance_training as base
from mcm_solarcheck.services import pvis_controlled_learning as learning
from test_cvut_cpu_runtime import runtime
from test_pvis_public_training import numeric_package
from test_pvis_controlled_learning import generated_corpus

pytestmark = pytest.mark.skipif(not os.environ.get('SOLARCHECK_TEST_CVUT_RUNTIME'),
    reason='Explicit isolated Torch CPU qualification only')


def test_full_adam_checkpoint_resume_matches_uninterrupted_and_show_loads_no_model(runtime, tmp_path, monkeypatch):
    torch, reference, spec = runtime
    package, old_manifest = numeric_package(tmp_path/'old-data')
    parent_output = tmp_path/'parent'
    outputs = (tmp_path/'resumed', tmp_path/'fresh')
    try:
        parent = base.run_training(package, old_manifest, reference, parent_output,
            allow_synthetic=True, parameters=dict(base.PARAMETERS, epochs=1))
        parent_job = parent_output/parent['run_id']; original = (parent_job/'report.json').read_bytes()
        folder, manifest = generated_corpus(tmp_path/'corpus')
        params = dict(learning.PARAMETERS, epochs=2, checkpoint_steps=1)
        ticks = iter((0., 2.))
        initial = learning.run(folder, manifest, parent_job, reference, outputs[0], synthetic=True,
            parameters=params, seconds=1, now=lambda: next(ticks))
        assert initial['status'] == 'checkpoint_available' and initial['saved_steps'] == 0
        assert learning.read_status(folder, manifest, parent_job, outputs[0]/initial['run_id'], synthetic=True) == initial
        def cancel():
            return bool(list(outputs[0].glob('*/checkpoint-00000001.pt')))
        partial = learning.run(folder, manifest, parent_job, reference, outputs[0], synthetic=True,
            parameters=params, should_cancel=cancel)
        assert partial['status'] == 'checkpoint_available' and partial['saved_steps'] == 1
        resumed = learning.run(folder, manifest, parent_job, reference, outputs[0], synthetic=True, parameters=params)
        assert resumed['status'] == 'finished_experimental_not_production' and resumed['saved_steps'] == 4
        assert resumed['reload_verified'] and resumed['ignore_gradient_verified'] and resumed['experimental_weights_changed']
        expected_state = resumed['last_training_state_sha256']; expected_metrics = resumed['selected_validation']
        with monkeypatch.context() as m:
            m.setattr(learning.factory, 'reference_model', lambda *a, **k: pytest.fail('Show constructed model'))
            assert learning.read_status(folder, manifest, parent_job, outputs[0]/resumed['run_id'], synthetic=True) == resumed
            assert learning.run(folder, manifest, parent_job, reference, outputs[0], synthetic=True, parameters=params) == resumed
        shutil.rmtree(outputs[0])
        fresh = learning.run(folder, manifest, parent_job, reference, outputs[1], synthetic=True, parameters=params)
        assert fresh['last_training_state_sha256'] == expected_state
        assert fresh['selected_validation'] == expected_metrics
        assert (parent_job/'report.json').read_bytes() == original
    finally:
        for path in (*outputs, parent_output):
            if path.exists(): shutil.rmtree(path)
