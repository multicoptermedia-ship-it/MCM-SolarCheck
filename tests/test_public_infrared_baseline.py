"""Public IR: first honest experimental image-level evaluation, no model rollout."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from mcm_solarcheck.offline.public_infrared_baseline import (
    exploratory_split, run_public_infrared_baseline,
)
from mcm_solarcheck.services.pv_public_infrared_source import DATASET_ID


def _catalog(tmp_path):
    root = tmp_path / "research"
    images = root / "images"
    images.mkdir(parents=True)
    rows = []
    # Deliberately create both classes in every image-level split.
    for color, label in ((40, "No-Anomaly"), (220, "Cell")):
        found = {"train": 0, "validation": 0, "test": 0}
        for n in range(10_000):
            key = f"x{color}-{n}"
            split = exploratory_split(key)
            if found[split] >= (3 if split == "train" else 2):
                continue
            found[split] += 1
            buffer = BytesIO()
            Image.new("L", (24, 40), color=color).save(buffer, "JPEG")
            data = buffer.getvalue()
            (images / f"{key}.jpg").write_bytes(data)
            rows.append({
                "source_id": key, "image": f"images/{key}.jpg",
                "class": label, "sha256": sha256(data).hexdigest(),
            })
            if found == {"train": 3, "validation": 2, "test": 2}:
                break
        assert found == {"train": 3, "validation": 2, "test": 2}
    cat = root / "public-infrared-index.json"
    cat.write_text(json.dumps({
        "dataset_id": DATASET_ID,
        "archive_sha256": "1" * 64,
        "status": "exploratory_only_not_approved_for_reports",
        "site_grouping": "not_available_no_site_disjoint_validation",
        "samples": rows,
    }), encoding="utf-8")
    return cat, rows


def test_baseline_on_synthetic_images_reports_holdout_but_never_release(tmp_path):
    cat, rows = _catalog(tmp_path)
    target = tmp_path / "experimental-results.json"
    evaluation = run_public_infrared_baseline(cat, target)
    assert target.is_file()
    assert evaluation["train"]["samples"] == 6
    assert evaluation["validation"]["samples"] == 4
    assert evaluation["test"]["samples"] == 4
    assert evaluation["validation"]["accuracy"] == 1.0
    assert evaluation["test"]["accuracy"] == 1.0
    assert "no_site" not in evaluation["status"]
    assert evaluation["status"] == "experimental_no_report_or_model_approval"
    assert "site/physical-module" in evaluation["split_warning"]
    assert not (tmp_path / "solarcheck.sqlite3").exists()
    with pytest.raises(PermissionError):
        run_public_infrared_baseline(cat, target)


def test_bad_training_image_hash_does_not_create_metrics(tmp_path):
    cat, rows = _catalog(tmp_path)
    row = rows[0]
    (cat.parent / row["image"]).write_bytes(b"altered, not a JPEG")
    with pytest.raises(PermissionError, match="hash"):
        run_public_infrared_baseline(cat, tmp_path / "should-not-exist.json")
    assert not (tmp_path / "should-not-exist.json").exists()


def test_unsafe_or_promoted_catalog_rejected(tmp_path):
    cat, rows = _catalog(tmp_path)
    target = tmp_path / "metrics.json"
    data = json.loads(cat.read_text())
    data["status"] = "approved_for_commercial_reports"
    cat.write_text(json.dumps(data))
    with pytest.raises(PermissionError):
        run_public_infrared_baseline(cat, target)
    assert not target.exists()


def test_no_site_group_license_or_model_policy_is_mutated(tmp_path):
    cat, rows = _catalog(tmp_path)
    path = tmp_path / "experiment.json"
    run_public_infrared_baseline(cat, path)
    data = json.loads(path.read_text())
    assert data["method"] == "grayscale_nearest_class_centroid_baseline"
    assert "not radiometric" in data["limitations"]
    assert not list(tmp_path.rglob("*.pt"))
    assert not list(tmp_path.rglob("*.sqlite3"))
