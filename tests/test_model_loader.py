from hashlib import sha256

import pytest

from mcm_solarcheck.review.model_loader import load_verified_ultralytics_model
from mcm_solarcheck.review.model_manifest import ModelManifest


def _manifest(data):
    return ModelManifest(
        "pv-yolo", "v1", "thermal", "dataset", "license", sha256(data).hexdigest()
    )


def test_verified_weight_file_is_passed_to_injected_yolo_factory(tmp_path):
    path=tmp_path / "model.pt"
    path.write_bytes(b"verified")
    calls=[]
    model=load_verified_ultralytics_model(
        _manifest(b"verified"), path, yolo_factory=lambda value: calls.append(value) or object()
    )
    assert model is not None
    assert calls == [str(path)]


def test_tampered_weight_file_is_never_loaded(tmp_path):
    path=tmp_path / "model.pt"
    path.write_bytes(b"tampered")
    called=False
    def factory(value):
        nonlocal called
        called=True
        return object()
    with pytest.raises(ValueError):
        load_verified_ultralytics_model(_manifest(b"expected"), path, yolo_factory=factory)
    assert called is False
