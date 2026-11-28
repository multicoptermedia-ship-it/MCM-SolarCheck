"""Actual pinned four-channel U-Net inference/persistence; synthetic numeric crops only."""
import os
import shutil

import pytest

from mcm_solarcheck.services import pvis_instance_training as trained
from mcm_solarcheck.services import pvis_instance_validation as validation
from test_cvut_cpu_runtime import runtime
from test_pvis_public_training import numeric_package

pytestmark = pytest.mark.skipif(not os.environ.get('SOLARCHECK_TEST_CVUT_RUNTIME'),
    reason='Explicit isolated Torch CPU qualification only')


def test_actual_saved_four_channel_inference_cancel_resume_reopen_without_retraining(runtime, tmp_path, monkeypatch):
    _, reference, _ = runtime
    package, manifest = numeric_package(tmp_path/'package')
    output = tmp_path/'training'; results = tmp_path/'validation'
    try:
        parent = trained.run_training(package, manifest, reference, output, allow_synthetic=True,
            parameters=dict(trained.PARAMETERS, epochs=1))
        job = output/parent['run_id']; before = (job/'report.json').read_bytes()
        weights_before = trained._digest(job/trained.WEIGHTS)
        with monkeypatch.context() as m:
            m.setattr(trained, 'run_training', lambda *a, **k: pytest.fail('Validation retrained model'))
            with pytest.raises(KeyboardInterrupt):
                validation.run_validation(package, manifest, job, reference, results, allow_synthetic=True,
                    should_cancel=lambda: bool(list(results.glob('*/crop-*.json'))))
            assert len(list(results.glob('*/crop-*.json'))) == 1 and not list(results.glob('*/report.json'))
            first = next(results.glob('*/crop-*.json')); saved = first.read_bytes()
            result = validation.run_validation(package, manifest, job, reference, results, allow_synthetic=True)
            assert result['validation_crops'] == 2 and result['inference_images_by_split']['test'] == 0
            assert first.read_bytes() == saved
            assert all(result[k] is False for k in validation.FALSE_FLAGS)
            m.setattr(trained, 'reference_model', lambda *a, **k: pytest.fail('Reopen/reuse constructed model'))
            assert validation.read_result(package, manifest, job, results, result, allow_synthetic=True) == result
            assert validation.run_validation(package, manifest, job, reference, results, allow_synthetic=True) == result
        assert (job/'report.json').read_bytes() == before
        assert trained._digest(job/trained.WEIGHTS) == weights_before
    finally:
        if output.exists(): shutil.rmtree(output)
