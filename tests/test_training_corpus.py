from dataclasses import replace
import pytest

from mcm_solarcheck.review.training_corpus import index_m3t_training_sample


def test_new_m3t_image_is_indexed_but_not_trainable_before_review(tmp_path):
    path=tmp_path / "thermal.jpg"
    path.write_bytes(b"m3t-image")
    sample=index_m3t_training_sample("T-1", path, "thermal")
    assert sample.sample_id.startswith("thermal:")
    assert sample.label_status == "unlabeled"
    assert sample.rights_status == "unverified"
    assert sample.trainable is False


def test_training_requires_both_human_label_and_rights_approval(tmp_path):
    path=tmp_path / "thermal.jpg"
    path.write_bytes(b"m3t-image")
    sample=index_m3t_training_sample("T-1", path, "thermal")
    assert replace(sample, label_status="human_reviewed").trainable is False
    assert replace(sample, rights_status="approved").trainable is False
    assert replace(sample, label_status="human_reviewed", rights_status="approved").trainable is True


def test_training_sample_identity_is_content_deduplicated(tmp_path):
    first=tmp_path / "a.jpg"; second=tmp_path / "b.jpg"
    first.write_bytes(b"same"); second.write_bytes(b"same")
    assert index_m3t_training_sample("T-1", first, "thermal").sample_id == index_m3t_training_sample("T-2", second, "thermal").sample_id


def test_missing_source_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        index_m3t_training_sample("T-1", tmp_path / "missing.jpg", "thermal")
