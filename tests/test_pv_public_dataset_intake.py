import pytest

from mcm_solarcheck.services.pv_dataset_intake import (
    ImageModality, LicenseDecision, PublicDatasetRecord,
)
from mcm_solarcheck.services.pv_yolo_dataset_validation import (
    parse_yolo_detection_labels, validate_dataset_relative_path, validate_group_splits,
)


def test_unreviewed_public_dataset_cannot_train():
    dataset = PublicDatasetRecord("pv", "https://example.org/data", ImageModality.RGB, "unknown")
    assert not dataset.can_train_commercially(ImageModality.RGB)


def test_commercial_approval_needs_review_and_matching_modality():
    with pytest.raises(ValueError):
        PublicDatasetRecord("pv", "https://example.org/data", ImageModality.RGB,
                            "CC BY 4.0", LicenseDecision.APPROVED_COMMERCIAL)
    approved = PublicDatasetRecord("pv", "https://example.org/data", ImageModality.RGB,
                                   "CC BY 4.0", LicenseDecision.APPROVED_COMMERCIAL,
                                   "reviewer", "license-evidence")
    assert approved.can_train_commercially(ImageModality.RGB)
    assert not approved.can_train_commercially(ImageModality.THERMAL)


def test_noncommercial_license_is_rejected():
    with pytest.raises(ValueError):
        PublicDatasetRecord("el", "https://example.org/data", ImageModality.EL,
                            "CC BY-NC-SA 4.0", LicenseDecision.APPROVED_COMMERCIAL,
                            "reviewer", "license-evidence")


def test_yolo_label_parser_accepts_only_valid_boxes():
    parsed = parse_yolo_detection_labels("0 0.5 0.5 0.4 0.6\n", 2)
    assert len(parsed) == 1 and parsed[0].class_id == 0
    for invalid in ("2 0.5 0.5 0.2 0.2", "0 0.1 0.1 0.5 0.5",
                    "0 nan 0.5 0.2 0.2", "0 0.5 0.5 0 0.2", "0 1 2"):
        with pytest.raises(ValueError):
            parse_yolo_detection_labels(invalid, 2)


def test_group_split_rejects_site_leakage():
    validate_group_splits({"train": {"a"}, "val": {"b"}, "test": {"c"}})
    with pytest.raises(ValueError):
        validate_group_splits({"train": {"a"}, "val": {"a"}, "test": {"c"}})


def test_dataset_paths_reject_traversal():
    assert validate_dataset_relative_path("images/train/pv.jpg") == "images/train/pv.jpg"
    for path in ("../secret", "/tmp/image.jpg", "images\\x.jpg"):
        with pytest.raises(ValueError):
            validate_dataset_relative_path(path)
