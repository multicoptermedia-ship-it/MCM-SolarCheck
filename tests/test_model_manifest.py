import pytest

from mcm_solarcheck.review.model_manifest import ModelManifest


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
