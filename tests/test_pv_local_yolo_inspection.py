from pathlib import Path

import pytest

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind
from mcm_solarcheck.services.pv_dataset_intake import ImageModality, LicenseDecision, PublicDatasetRecord
from mcm_solarcheck.services.pv_local_yolo_inspection import inspect_local_yolo_dataset
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping


def _dataset(tmp_path: Path):
    (tmp_path / "labels").mkdir()
    (tmp_path / "images").mkdir()
    (tmp_path / "labels" / "sample.txt").write_text("0 0.5 0.5 0.4 0.4\n")
    (tmp_path / "images" / "sample.jpg").write_bytes(b"fake-jpeg-not-decoded")
    return tmp_path


def _record(approved=False):
    return PublicDatasetRecord("pv", "https://example.org/pv", ImageModality.RGB,
                               "CC BY 4.0",
                               LicenseDecision.APPROVED_COMMERCIAL if approved else LicenseDecision.UNREVIEWED,
                               "expert" if approved else None, "license-audit" if approved else None)


def test_local_inspection_is_read_only_and_license_gated(tmp_path):
    root = _dataset(tmp_path)
    mapping = YoloClassMapping(("crack",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)
    assert not inspect_local_yolo_dataset(root, _record(), mapping).training_allowed
    result = inspect_local_yolo_dataset(root, _record(True), mapping)
    assert (result.inspected_pairs, result.annotation_count, result.unmapped_annotations) == (1, 1, 0)
    assert result.training_allowed


def test_unmapped_class_cannot_be_training_ready(tmp_path):
    root = _dataset(tmp_path)
    mapping = YoloClassMapping(("unknown",), (None,), ImageModality.RGB)
    result = inspect_local_yolo_dataset(root, _record(True), mapping)
    assert result.unmapped_annotations == 1
    assert not result.training_allowed


def test_reject_cross_modality_mapping():
    with pytest.raises(ValueError):
        YoloClassMapping(("hotspot",), (ObservationKind.THERMAL_HOTSPOT,), ImageModality.RGB)


def test_reject_missing_image_and_invalid_box(tmp_path):
    root = _dataset(tmp_path)
    mapping = YoloClassMapping(("crack",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)
    (root / "images" / "sample.jpg").unlink()
    with pytest.raises(ValueError):
        inspect_local_yolo_dataset(root, _record(True), mapping)
    (root / "images" / "sample.jpg").write_bytes(b"fake-jpeg")
    (root / "labels" / "sample.txt").write_text("0 1.2 0.5 0.4 0.4\n")
    with pytest.raises(ValueError):
        inspect_local_yolo_dataset(root, _record(True), mapping)


def test_reject_symlink_and_count_overflow(tmp_path):
    root = _dataset(tmp_path)
    mapping = YoloClassMapping(("crack",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)
    with pytest.raises(ValueError):
        inspect_local_yolo_dataset(root, _record(True), mapping, max_pairs=0)
    (root / "labels" / "another.txt").write_text("")
    with pytest.raises(ValueError):
        inspect_local_yolo_dataset(root, _record(True), mapping, max_pairs=1)
