from io import BytesIO

import pytest
from PIL import Image

from mcm_solarcheck.services.pv_ai_fault_taxonomy import ObservationKind
from mcm_solarcheck.services.pv_dataset_intake import ImageModality, LicenseDecision, PublicDatasetRecord
from mcm_solarcheck.services.pv_training_image_quality import inspect_training_image
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping
from mcm_solarcheck.services.pv_yolo_dataset_audit import audit_local_yolo_dataset


def _fixture(root):
    sites = {}
    for split, site in (("train", "site-a"), ("val", "site-b"), ("test", "site-c")):
        images = root / "images" / split
        labels = root / "labels" / split
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        image = images / "sample.png"
        Image.new("RGB", (64, 64), "white").save(image)
        (labels / "sample.txt").write_text("0 0.5 0.5 0.4 0.4\n", encoding="utf-8")
        sites[split + "/sample.png"] = site
    return sites


def _approved():
    return PublicDatasetRecord("source", "https://example.org/dataset", ImageModality.RGB,
                               "CC BY 4.0", LicenseDecision.APPROVED_COMMERCIAL,
                               "reviewer", "license-proof")


def _mapping():
    return YoloClassMapping(("glass",), (ObservationKind.RGB_GLASS_DAMAGE,), ImageModality.RGB)


def test_real_images_and_disjoint_sites(tmp_path):
    sites = _fixture(tmp_path)
    result = audit_local_yolo_dataset(tmp_path, _approved(), _mapping(), sites)
    assert (result.images, result.annotations, result.negative_images) == (3, 3, 0)
    assert result.training_ready


def test_corrupt_image_rejected(tmp_path):
    sites = _fixture(tmp_path)
    image = tmp_path / "images/train/sample.png"
    image.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        audit_local_yolo_dataset(tmp_path, _approved(), _mapping(), sites)


def test_site_leakage_rejected(tmp_path):
    sites = _fixture(tmp_path)
    sites["test/sample.png"] = "site-a"
    with pytest.raises(ValueError):
        audit_local_yolo_dataset(tmp_path, _approved(), _mapping(), sites)


def test_missing_label_rejected(tmp_path):
    sites = _fixture(tmp_path)
    (tmp_path / "labels/val/sample.txt").unlink()
    with pytest.raises(ValueError):
        audit_local_yolo_dataset(tmp_path, _approved(), _mapping(), sites)


def test_unreviewed_license_not_training_ready(tmp_path):
    sites = _fixture(tmp_path)
    record = PublicDatasetRecord("source", "https://example.org/dataset", ImageModality.RGB, "unknown")
    assert not audit_local_yolo_dataset(tmp_path, record, _mapping(), sites).training_ready


def test_empty_annotation_is_valid_negative_example(tmp_path):
    sites = _fixture(tmp_path)
    (tmp_path / "labels/train/sample.txt").write_text("", encoding="utf-8")
    result = audit_local_yolo_dataset(tmp_path, _approved(), _mapping(), sites)
    assert result.negative_images == 1 and result.annotations == 2


def test_reject_image_too_small(tmp_path):
    sites = _fixture(tmp_path)
    Image.new("RGB", (8, 8)).save(tmp_path / "images/train/sample.png")
    with pytest.raises(ValueError):
        audit_local_yolo_dataset(tmp_path, _approved(), _mapping(), sites)
