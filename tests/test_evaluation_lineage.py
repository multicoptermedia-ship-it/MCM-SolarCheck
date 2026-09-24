import pytest

from mcm_solarcheck.review.evaluation_lineage import EvaluationSet, IndependentModelEvaluation, require_independent_evaluation
from mcm_solarcheck.review.model_lineage import TrainingRun
from mcm_solarcheck.review.model_validation import ModelValidationSummary


def _run():
    return TrainingRun("d"*64,"s"*64,"ultralytics","8.3","rendered_rgb",{"seed":42})


def _summary(representative=True):
    return ModelValidationSummary(20,5,4,1,representative,"validator")


def test_independent_evaluation_requires_distinct_dataset_and_snapshot():
    run=_run()
    valid=IndependentModelEvaluation(EvaluationSet("e"*64,"v"*64,True),_summary())
    require_independent_evaluation(run,valid)
    with pytest.raises(ValueError,match="dataset"):
        require_independent_evaluation(run,IndependentModelEvaluation(EvaluationSet(run.dataset_id,"v"*64,True),_summary()))
    with pytest.raises(ValueError,match="snapshot"):
        require_independent_evaluation(run,IndependentModelEvaluation(EvaluationSet("e"*64,run.snapshot_id,True),_summary()))


def test_evaluation_provenance_must_match_representative_flag():
    with pytest.raises(ValueError,match="provenance"):
        IndependentModelEvaluation(EvaluationSet("e"*64,"v"*64,False),_summary(True))


def test_evaluation_id_is_deterministic():
    a=EvaluationSet("e"*64,"v"*64,True)
    b=EvaluationSet("e"*64,"v"*64,True)
    assert a.evaluation_id==b.evaluation_id
