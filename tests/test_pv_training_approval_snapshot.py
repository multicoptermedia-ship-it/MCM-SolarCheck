import pytest
from PIL import Image

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind
from mcm_solarcheck.services.pv_dataset_intake import ImageModality, LicenseDecision, PublicDatasetRecord
from mcm_solarcheck.services.pv_training_approval_gate import require_matching_training_approval
from mcm_solarcheck.services.pv_training_approval_snapshot import (
    prepare_training_approval_snapshot, verify_training_approval_snapshot,
)
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping


def _data(root):
    groups = {}
    for split, site in (("train", "a"), ("val", "b"), ("test", "c")):
        images = root / "images" / split
        labels = root / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        Image.new("RGB", (64, 64), "white").save(images / "pv.png")
        (labels / "pv.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        groups[split + "/pv.png"] = site
    return groups


def _record(evidence="license-approval"):
    return PublicDatasetRecord("pv-source", "https://example.org/pv", ImageModality.RGB,
                               "CC BY 4.0", LicenseDecision.APPROVED_COMMERCIAL,
                               "reviewer", evidence)


def _mapping():
    return YoloClassMapping(("glass",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)


def _snapshot(root, groups):
    return prepare_training_approval_snapshot(root, _record(), _mapping(), groups,
        model_reference="reviewed-local-model", weights_license_review_reference="model-license-proof")


def test_snapshot_matches_unchanged_dataset(tmp_path):
    groups = _data(tmp_path)
    snapshot = _snapshot(tmp_path, groups)
    assert verify_training_approval_snapshot(tmp_path, groups, snapshot)
    assert snapshot.plan.status == "plan_only_no_training"
    require_matching_training_approval(tmp_path, _record(), _mapping(), groups, snapshot)


def test_changed_label_invalidates_snapshot(tmp_path):
    groups = _data(tmp_path)
    snapshot = _snapshot(tmp_path, groups)
    (tmp_path / "labels/train/pv.txt").write_text("0 0.5 0.5 0.4 0.4\n")
    assert not verify_training_approval_snapshot(tmp_path, groups, snapshot)
    with pytest.raises(PermissionError):
        require_matching_training_approval(tmp_path, _record(), _mapping(), groups, snapshot)


def test_changed_group_manifest_invalidates_snapshot(tmp_path):
    groups = _data(tmp_path)
    snapshot = _snapshot(tmp_path, groups)
    groups["train/pv.png"] = "changed-site"
    assert not verify_training_approval_snapshot(tmp_path, groups, snapshot)


def test_changed_license_evidence_invalidates_snapshot(tmp_path):
    groups = _data(tmp_path)
    snapshot = _snapshot(tmp_path, groups)
    with pytest.raises(PermissionError):
        require_matching_training_approval(tmp_path, _record("different-approval"),
                                           _mapping(), groups, snapshot)


def test_unreviewed_license_cannot_be_snapshotted(tmp_path):
    groups = _data(tmp_path)
    unreviewed = PublicDatasetRecord("pv-source", "https://example.org/pv",
                                     ImageModality.RGB, "unknown")
    with pytest.raises(PermissionError):
        prepare_training_approval_snapshot(tmp_path, unreviewed, _mapping(), groups,
            model_reference="local", weights_license_review_reference="review")
