import pytest
from PIL import Image

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind
from mcm_solarcheck.services.pv_dataset_intake import ImageModality, LicenseDecision, PublicDatasetRecord
from mcm_solarcheck.services.pv_training_dataset_fingerprint import fingerprint_local_yolo_dataset
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping
from mcm_solarcheck.services.pv_yolo_dataset_audit import audit_local_yolo_dataset
from mcm_solarcheck.services.pv_yolo_training_plan import prepare_yolo_training_plan


def _setup(root):
    groups = {}
    for split, site in (("train", "one"), ("val", "two"), ("test", "three")):
        image_dir, label_dir = root / "images" / split, root / "labels" / split
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        Image.new("RGB", (64, 64), "white").save(image_dir / "panel.png")
        (label_dir / "panel.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        groups[split + "/panel.png"] = site
    return groups


def _approved():
    return PublicDatasetRecord("source", "https://example.org/pv", ImageModality.RGB,
                               "CC BY 4.0", LicenseDecision.APPROVED_COMMERCIAL, "expert", "license-proof")


def test_fingerprint_stable_and_changes_with_annotations(tmp_path):
    _setup(tmp_path)
    original = fingerprint_local_yolo_dataset(tmp_path)
    assert original.file_count == 6
    assert original == fingerprint_local_yolo_dataset(tmp_path)
    (tmp_path / "labels/train/panel.txt").write_text("0 0.5 0.5 0.3 0.3\n")
    assert original.digest_sha256 != fingerprint_local_yolo_dataset(tmp_path).digest_sha256


def test_plan_requires_audit_and_model_license(tmp_path):
    groups = _setup(tmp_path)
    mapping = YoloClassMapping(("crack",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)
    audit = audit_local_yolo_dataset(tmp_path, _approved(), mapping, groups)
    fingerprint = fingerprint_local_yolo_dataset(tmp_path)
    plan = prepare_yolo_training_plan(_approved(), mapping, audit, fingerprint,
                                      model_reference="local-reviewed-model",
                                      weights_license_review_reference="weights-approval")
    assert plan.status == "plan_only_no_training"
    assert plan.dataset_sha256 == fingerprint.digest_sha256
    with pytest.raises(ValueError):
        prepare_yolo_training_plan(_approved(), mapping, audit, fingerprint,
                                   model_reference="local-reviewed-model",
                                   weights_license_review_reference="")
    with pytest.raises(ValueError):
        prepare_yolo_training_plan(_approved(), mapping, audit, fingerprint,
                                   epochs=0, model_reference="local-reviewed-model",
                                   weights_license_review_reference="approval")


def test_fingerprint_rejects_symlinks_and_limits(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ValueError):
        fingerprint_local_yolo_dataset(tmp_path, max_files=5)
    with pytest.raises(ValueError):
        fingerprint_local_yolo_dataset(tmp_path, max_total_bytes=1)
