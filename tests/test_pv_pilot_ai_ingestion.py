"""Block 38: offline-first AI staging contract shared with online adapters."""

import pytest

from mcm_solarcheck.services.pv_pilot_ai_ingestion import (
    LocalAIResult,
    stage_local_ai_result,
)


def _result(**overrides):
    values = {
        "module": "PV-001",
        "status": "classified_suspicion",
        "model_id": "local-detector",
        "model_version": "1.0",
        "input_reference": "offline/image-001",
        "suggested_cause": "Hotspot",
        "confidence": 0.81,
    }
    values.update(overrides)
    return LocalAIResult(**values)


def test_offline_detection_is_staged_for_human_review():
    assessment = stage_local_ai_result(_result())
    assert assessment.status == "classified_suspicion"
    assert assessment.suggested_cause == "Hotspot"
    assert assessment.expert_assessment is None
    assert assessment.provenance.reviewer_decision == "pending"
    assert assessment.provenance.input_reference == "offline/image-001"


@pytest.mark.parametrize("module", ["", " ", None, 123])
def test_module_reference_is_required(module):
    with pytest.raises(ValueError):
        _result(module=module)


@pytest.mark.parametrize("field", ["model_id", "model_version", "input_reference"])
def test_model_provenance_is_required(field):
    with pytest.raises(ValueError):
        stage_local_ai_result(_result(**{field: " "}))


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf"), True])
def test_invalid_confidence_is_rejected(confidence):
    with pytest.raises(ValueError):
        stage_local_ai_result(_result(confidence=confidence))


@pytest.mark.parametrize("status,cause", [
    ("approved", "Hotspot"),
    ("classified_suspicion", None),
    ("unassigned", "Hotspot"),
    ("no_anomaly", "Hotspot"),
])
def test_invalid_assessment_is_rejected(status, cause):
    with pytest.raises(ValueError):
        stage_local_ai_result(_result(status=status, suggested_cause=cause))


def test_staging_rejects_untyped_input():
    with pytest.raises(TypeError):
        stage_local_ai_result({"status": "classified_suspicion"})


def test_unreviewed_detection_cannot_become_customer_report_finding():
    from mcm_solarcheck.services.pv_report_pilot_contract import PilotFinding, PilotReport

    assessment = stage_local_ai_result(_result())
    unreviewed = PilotFinding(
        module="PV-001",
        observation="KI-Vorschlag: Hotspot",
        reviewed=False,
        ai_assessment=assessment,
    )
    with pytest.raises(PermissionError, match="expert review"):
        PilotReport(
            project="Offline-Test",
            inspection_date="2026-10-13",
            inspector="Test",
            plant="PV-Test",
            conditions=None,
            limitations="Nur Testdaten",
            findings=(unreviewed,),
        )
