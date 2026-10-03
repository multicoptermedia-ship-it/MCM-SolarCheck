import pytest

from hashlib import sha256

from mcm_solarcheck.review.model_manifest import ModelManifest, verify_weights_sha256


def test_model_manifest_records_external_model_provenance():
    digest="a"*64
    manifest=ModelManifest("pv-yolo", "v1", "thermal", "dataset-release-1", "CC-BY-4.0", digest)
    assert manifest.modality == "thermal"
    assert manifest.weights_sha256 == digest


@pytest.mark.parametrize("field", ["provider", "model_version", "dataset", "license_id"])
def test_required_model_provenance_cannot_be_blank(field):
    values=dict(provider="pv-yolo", model_version="v1", modality="thermal",
                dataset="dataset-release-1", license_id="CC-BY-4.0")
    values[field]=" "
    with pytest.raises(ValueError):
        ModelManifest(**values)


@pytest.mark.parametrize("modality", ["", "mixed", "infrared"])
def test_model_manifest_restricts_modality(modality):
    with pytest.raises(ValueError):
        ModelManifest("pv-yolo", "v1", modality, "dataset", "license")


@pytest.mark.parametrize("digest", ["abc", "g"*64, "a"*63, "a"*65])
def test_model_manifest_rejects_invalid_weight_digest(digest):
    with pytest.raises(ValueError):
        ModelManifest("pv-yolo", "v1", "thermal", "dataset", "license", digest)


def test_weight_artifact_digest_is_verified(tmp_path):
    weights=tmp_path / "model.pt"
    weights.write_bytes(b"fixture-weights")
    digest=sha256(b"fixture-weights").hexdigest()
    manifest=ModelManifest("pv-yolo", "v1", "thermal", "dataset", "license", digest)
    assert verify_weights_sha256(manifest, weights) is True


def test_weight_artifact_digest_mismatch_fails_verification(tmp_path):
    weights=tmp_path / "model.pt"
    weights.write_bytes(b"unexpected")
    manifest=ModelManifest("pv-yolo", "v1", "thermal", "dataset", "license", "a"*64)
    assert verify_weights_sha256(manifest, weights) is False


def test_weight_verification_requires_recorded_digest(tmp_path):
    weights=tmp_path / "model.pt"
    weights.write_bytes(b"fixture")
    manifest=ModelManifest("pv-yolo", "v1", "thermal", "dataset", "license")
    with pytest.raises(ValueError):
        verify_weights_sha256(manifest, weights)


def test_model_manifest_can_record_preprocessing_and_backend():
    manifest=ModelManifest(
        "pv-yolo", "v1", "thermal", "dataset", "license",
        preprocessing="radiometric-rjpeg-render-v1", backend="ultralytics-8.x",
    )
    assert manifest.preprocessing == "radiometric-rjpeg-render-v1"
    assert manifest.backend == "ultralytics-8.x"


@pytest.mark.parametrize("field", ["preprocessing", "backend"])
def test_optional_runtime_provenance_cannot_be_blank(field):
    values=dict(provider="pv-yolo", model_version="v1", modality="thermal",
                dataset="dataset", license_id="license", **{field: " "})
    with pytest.raises(ValueError):
        ModelManifest(**values)
