import pytest
from PIL import Image

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind
from mcm_solarcheck.services.pv_dataset_intake import ImageModality, LicenseDecision, PublicDatasetRecord
from mcm_solarcheck.services.pv_training_approval_snapshot import prepare_training_approval_snapshot
from mcm_solarcheck.services.pv_training_local_staging import stage_approved_local_yolo_dataset
from mcm_solarcheck.services.pv_training_staged_verification import require_verified_local_training_stage
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping


def _fixture(root):
    groups = {}
    for split, site in (("train", "a"), ("val", "b"), ("test", "c")):
        images, labels = root / "images" / split, root / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        Image.new("RGB", (64, 64), "white").save(images / "panel.png")
        (labels / "panel.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        groups[split + "/panel.png"] = site
    record = PublicDatasetRecord("pv", "https://example.org/pv", ImageModality.RGB,
        "CC BY 4.0", LicenseDecision.APPROVED_COMMERCIAL, "reviewer", "evidence")
    mapping = YoloClassMapping(("glass",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)
    approval = prepare_training_approval_snapshot(root, record, mapping, groups,
        model_reference="local-reviewed-model", weights_license_review_reference="weights-license")
    return groups, record, mapping, approval


def test_stages_and_verifies_only_local_data(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    groups, record, mapping, approval = _fixture(source)
    stage = stage_approved_local_yolo_dataset(source, tmp_path / "staged", record, mapping, groups, approval)
    assert stage.file_count == 6
    assert stage.status == "staged_no_training"
    require_verified_local_training_stage(stage, approval)


def test_changed_source_refused(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    groups, record, mapping, approval = _fixture(source)
    (source / "labels/train/panel.txt").write_text("0 0.5 0.5 0.3 0.3\n")
    with pytest.raises(PermissionError):
        stage_approved_local_yolo_dataset(source, tmp_path / "staged", record, mapping, groups, approval)
    assert not (tmp_path / "staged").exists()


def test_destination_inside_source_refused(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    groups, record, mapping, approval = _fixture(source)
    with pytest.raises(ValueError):
        stage_approved_local_yolo_dataset(source, source / "staged", record, mapping, groups, approval)


def test_staging_limit_cleans_up(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    groups, record, mapping, approval = _fixture(source)
    target = tmp_path / "staged"
    with pytest.raises(ValueError):
        stage_approved_local_yolo_dataset(source, target, record, mapping, groups, approval,
                                           max_total_bytes=1)
    assert not target.exists()
