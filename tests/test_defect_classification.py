from dataclasses import replace

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.classification import (
    DefectClassification,
    attach_classification_suggestion,
)
from mcm_solarcheck.review.findings import ReviewStatus, review_finding


def _finding():
    return Finding("F-1", "T-1", 10, 20, module_id="M-0042")


def test_classifier_suggestion_is_advisory_and_auditable():
    finding=_finding()
    suggestion=DefectClassification("hotspot_candidate", .82, "fixture-model", "1.0")
    classified=attach_classification_suggestion(finding, suggestion)
    assert classified.reviewer_status == "unreviewed"
    assert classified.metadata["classification_status"] == "suggested"
    assert classified.metadata["classification_label"] == "hotspot_candidate"
    assert classified.metadata["classification_provider"] == "fixture-model"
    assert classified.metadata["classification_model_version"] == "1.0"


def test_human_review_remains_authoritative_after_machine_suggestion():
    classified=attach_classification_suggestion(
        _finding(), DefectClassification("hotspot_candidate", .82, "fixture-model")
    )
    reviewed, audit=review_finding(
        classified, status=ReviewStatus.REJECTED, reviewer="Inspector"
    )
    assert reviewed.reviewer_status == "rejected"
    assert reviewed.metadata["review_source"] == "human"
    assert reviewed.metadata["classification_label"] == "hotspot_candidate"
    assert audit.status == ReviewStatus.REJECTED


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -.01, 1.01])
def test_invalid_classifier_confidence_fails_closed(confidence):
    with pytest.raises(ValueError):
        DefectClassification("hotspot_candidate", confidence, "fixture-model")


@pytest.mark.parametrize("label,provider", [("", "model"), ("hotspot", ""), (" ", "model"), ("hotspot", " ")])
def test_classifier_requires_auditable_identity(label, provider):
    with pytest.raises(ValueError):
        DefectClassification(label, .5, provider)


def test_classification_modality_is_auditable_and_restricted():
    suggestion=DefectClassification("hotspot_candidate", .8, "fixture-model", "1.0", "thermal")
    classified=attach_classification_suggestion(_finding(), suggestion)
    assert classified.metadata["classification_modality"] == "thermal"
    with pytest.raises(ValueError):
        DefectClassification("hotspot_candidate", .8, "fixture-model", "1.0", "mixed")


@pytest.mark.parametrize("version", ["", " ", "\t"])
def test_blank_model_version_fails_closed(version):
    with pytest.raises(ValueError):
        DefectClassification("hotspot_candidate", .8, "fixture-model", version, "thermal")
