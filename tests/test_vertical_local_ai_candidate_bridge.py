"""Block 38: local AI suggestions enter the existing explicit expert review workflow."""
import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.services.pv_pilot_ai_ingestion import LocalAIResult
from mcm_solarcheck.services.vertical_local_ai_candidate_bridge import (
    LocalAICandidate, stage_local_ai_candidates,
)
from mcm_solarcheck.services.vertical_local_review_draft import LocalReviewDraft
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis


def _analysis():
    return ImportedCandidateAnalysis(1, 1, (
        Finding("imported-1", "thermal-1", 10, 11, module_id="module-1"),
    ))


def _candidate(**changes):
    fields = dict(finding_id="ai-1", thermal_frame_id="thermal-1", pixel_x=12,
                  pixel_y=14, result=LocalAIResult(
                      module="module-1", status="classified_suspicion",
                      model_id="local-model", model_version="v1",
                      input_reference="thermal-1", suggested_cause="Hotspot",
                      confidence=0.8))
    fields.update(changes)
    return LocalAICandidate(**fields)


def test_staged_ai_candidate_requires_manual_review():
    original = _analysis()
    staged = stage_local_ai_candidates(original, (_candidate(),))
    assert len(original.candidates) == 1
    assert len(staged.candidates) == 2
    assert staged.candidates[-1].reviewer_status == "unreviewed"
    assert staged.candidates[-1].finding_type == "local_ai_suggestion_unverified"
    draft = LocalReviewDraft(staged)
    assert draft.remaining == 2
    with pytest.raises(ValueError, match="explicit decision"):
        draft.finalize(reviewer_id="expert", evidence_reference="signed", approve_report=True)


@pytest.mark.parametrize("change", [
    {"finding_id": "imported-1"}, {"finding_id": ""},
    {"thermal_frame_id": ""}, {"pixel_x": -1}, {"pixel_y": True},
])
def test_invalid_identity_or_geometry_rejected(change):
    with pytest.raises(ValueError):
        stage_local_ai_candidates(_analysis(), (_candidate(**change),))


def test_duplicate_ai_ids_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        stage_local_ai_candidates(_analysis(), (_candidate(), _candidate()))


def test_invalid_ai_payload_is_rejected():
    bad = LocalAIResult("module-1", "approved", "model", "v1", "thermal-1")
    with pytest.raises(ValueError):
        stage_local_ai_candidates(_analysis(), (_candidate(result=bad),))


def test_unknown_thermal_frame_is_rejected():
    with pytest.raises(ValueError, match="known imported thermal evidence"):
        stage_local_ai_candidates(_analysis(), (_candidate(thermal_frame_id="unknown"),))


def test_model_input_must_match_thermal_frame():
    mismatch = LocalAIResult(
        "module-1", "unassigned", "local-model", "v1", "other-frame"
    )
    with pytest.raises(ValueError, match="input reference must match"):
        stage_local_ai_candidates(_analysis(), (_candidate(result=mismatch),))


def test_unpaired_analysis_is_rejected():
    analysis = ImportedCandidateAnalysis(0, 1, _analysis().candidates)
    with pytest.raises(ValueError, match="paired RGB and thermal"):
        stage_local_ai_candidates(analysis, (_candidate(),))


def test_batch_validation_is_atomic():
    analysis = _analysis()
    with pytest.raises(ValueError, match="duplicate"):
        stage_local_ai_candidates(analysis, (_candidate(), _candidate()))
    assert len(analysis.candidates) == 1


def test_unknown_module_is_rejected():
    unknown = LocalAIResult(
        "unknown-module", "unassigned", "local-model", "v1", "thermal-1"
    )
    with pytest.raises(ValueError, match="known imported module evidence"):
        stage_local_ai_candidates(_analysis(), (_candidate(result=unknown),))


def test_module_must_have_imported_evidence():
    missing = ImportedCandidateAnalysis(1, 1, (
        Finding("imported-1", "thermal-1", 10, 11),
    ))
    with pytest.raises(ValueError, match="known imported module evidence"):
        stage_local_ai_candidates(missing, (_candidate(),))
