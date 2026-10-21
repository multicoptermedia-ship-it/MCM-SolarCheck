"""No license-fee/default-cloud model: fail-closed, local seeded OSS policy."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from threading import Event

import pytest

from mcm_solarcheck.services.offline_ai_open_source import (
    LOCAL_BACKEND, LocalCheckpointProvenance, digest_file,
    encode_provenance, manifest_path, verify_local_checkpoint,
)
from mcm_solarcheck.services.offline_training_preflight import (
    OfflineTrainerConfiguration, VerifiedOfflineDataset,
)
from mcm_solarcheck.services.offline_torchvision_classifier import (
    local_resnet18_trainer,
)
from mcm_solarcheck.offline import ai_setup


def fake_checkpoint(tmp_path, *, classes=2, seed=41):
    weights = tmp_path / "local-resnet18-init.pt"
    weights.write_bytes(b"FAKE TORCH WEIGHTS -- ONLY A MANIFEST TEST")
    value = LocalCheckpointProvenance(
        digest_file(weights), "2.5.0", "0.20.0", classes, seed,
    )
    manifest_path(weights).write_bytes(encode_provenance(value))
    return weights, value


def test_manifest_roundtrip_checks_hash_and_classes(tmp_path):
    weights, record = fake_checkpoint(tmp_path)
    assert verify_local_checkpoint(weights) == record
    assert verify_local_checkpoint(
        weights, expected_sha256=record.weights_sha256, class_count=2,
    ) == record
    with pytest.raises(PermissionError, match="class count"):
        verify_local_checkpoint(weights, class_count=3)
    with pytest.raises(PermissionError, match="checkpoint is different"):
        verify_local_checkpoint(weights, expected_sha256="a" * 64)
    weights.write_bytes(b"tampered checkpoint bytes")
    with pytest.raises(PermissionError, match="checkpoint is different"):
        verify_local_checkpoint(weights)


@pytest.mark.parametrize("field,value", [
    ("backend", "ultralytics"),
    ("weights_origin", "downloaded-unknown-model"),
    ("initialization", "weights=DEFAULT"),
    ("architecture", "unsafe arbitrary code"),
    ("schema", 9),
    ("upstream_license_review", "unknown"),
])
def test_provenance_refuses_nonlocal_or_unreviewed_model(tmp_path, field, value):
    weights, _ = fake_checkpoint(tmp_path)
    location = manifest_path(weights)
    body = json.loads(location.read_text(encoding="utf-8"))
    body[field] = value
    location.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(PermissionError):
        verify_local_checkpoint(weights)


def test_symlinked_checkpoint_and_policy_are_denied(tmp_path):
    weights, _ = fake_checkpoint(tmp_path)
    other = tmp_path / "another.pt"
    try:
        other.symlink_to(weights)
    except (OSError, NotImplementedError):
        pytest.skip("Windows account cannot create symlinks")
    with pytest.raises(PermissionError):
        verify_local_checkpoint(other)


def test_local_policy_enables_only_matching_seed_and_fixed_local_model(tmp_path):
    db = tmp_path / "inspection.sqlite3"
    db.write_bytes(b"test only, never opened as a real DB")
    weights, provenance = fake_checkpoint(tmp_path)
    config = ai_setup.config_path_for_database(db)
    config.write_text(json.dumps({
        "schema": 1, "backend": LOCAL_BACKEND, "enabled": True,
        "weights_file": "local-resnet18-init.pt",
        "sha256": provenance.weights_sha256,
        "classes": 2, "seed": 41, "epochs": 1,
        "torchvision_version": "0.20.0",
        "license_review": "local-init-no-external-pretrained-weights",
    }), encoding="utf-8")
    selected, runner = ai_setup.load_local_torchvision_training(db)
    assert selected.backend == LOCAL_BACKEND
    assert selected.model_weights == weights
    assert selected.model_sha256 == provenance.weights_sha256
    assert selected.backend_version == "0.20.0"
    assert runner is local_resnet18_trainer
    with pytest.raises(FileExistsError):
        ai_setup.initialize_local_policy(db, classes=2, seed=41, epochs=1)


def test_policy_denies_user_supplied_checkpoint_url_and_disabled_backend(tmp_path):
    db = tmp_path / "inspection.sqlite3"
    db.touch()
    weights, evidence = fake_checkpoint(tmp_path)
    config = ai_setup.config_path_for_database(db)
    original = {
        "schema": 1, "backend": LOCAL_BACKEND, "enabled": True,
        "weights_file": "local-resnet18-init.pt",
        "sha256": evidence.weights_sha256, "classes": 2,
        "seed": 41, "epochs": 1,
        "torchvision_version": "0.20.0",
        "license_review": "local-init-no-external-pretrained-weights",
    }
    for change in (
        {"weights_file": "https://example.org/untrusted.pt"},
        {"backend": "proprietary-cloud"},
        {"enabled": False},
        {"sha256": "0" * 64},
        {"license_review": "purchased-enterprise"},
        {"classes": 5},
    ):
        config.write_text(json.dumps({**original, **change}), encoding="utf-8")
        with pytest.raises((ValueError, PermissionError, TypeError)):
            ai_setup.load_local_torchvision_training(db)
    config.unlink()
    assert ai_setup.load_local_torchvision_training(db) is None
    assert weights.read_bytes().startswith(b"FAKE")


def test_explicit_initialize_writes_versioned_policy_without_importing_torch(
    tmp_path, monkeypatch,
):
    db = tmp_path / "inspection.sqlite3"
    db.touch()
    from mcm_solarcheck.services import offline_torchvision_classifier as module

    def fake_initialize(path, *, classes, seed):
        assert path == tmp_path / "local-resnet18-init.pt"
        assert classes == 3 and seed == 77
        path.write_bytes(b"LOCAL FAKE - NO PYTORCH LOADED")
        proof = LocalCheckpointProvenance(
            digest_file(path), "2.5.0", "0.20.0", classes, seed,
        )
        manifest_path(path).write_bytes(encode_provenance(proof))
        return proof

    monkeypatch.setattr(module, "initialize_local_resnet18", fake_initialize)
    policy = ai_setup.initialize_local_policy(db, classes=3, seed=77, epochs=2)
    assert policy == tmp_path / "offline-ai-config.json"
    actual = json.loads(policy.read_text(encoding="utf-8"))
    assert actual["classes"] == 3
    assert actual["epochs"] == 2
    assert actual["sha256"] == sha256(
        b"LOCAL FAKE - NO PYTORCH LOADED",
    ).hexdigest()
    assert ai_setup.load_local_torchvision_training(db)[0].epochs == 2
    with pytest.raises(FileExistsError):
        ai_setup.initialize_local_policy(db, classes=3, seed=77, epochs=2)


def test_unprovisioned_desktop_has_no_ai_runner(tmp_path):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from mcm_solarcheck.offline.entrypoint import build_offline_window

    app = QApplication.instance() or QApplication([])
    window = build_offline_window(tmp_path / "empty.sqlite3")
    try:
        assert window._offline_report_training._training_jobs is None
        assert not (tmp_path / "offline-ai-config.json").exists()
        assert not (tmp_path / "local-resnet18-init.pt").exists()
    finally:
        window.close()


def test_existing_local_policy_loads_without_model_download(tmp_path):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from mcm_solarcheck.offline.entrypoint import build_offline_window

    app = QApplication.instance() or QApplication([])
    db = tmp_path / "offline.sqlite3"
    weights, proof = fake_checkpoint(tmp_path)
    policy = {
        "schema": 1, "backend": LOCAL_BACKEND, "enabled": True,
        "weights_file": "local-resnet18-init.pt",
        "sha256": proof.weights_sha256, "classes": 2,
        "seed": 41, "epochs": 1,
        "torchvision_version": "0.20.0",
        "license_review": "local-init-no-external-pretrained-weights",
    }
    (tmp_path / "offline-ai-config.json").write_text(
        json.dumps(policy), encoding="utf-8",
    )
    window = build_offline_window(db)
    try:
        assert window._offline_report_training._training_jobs is not None
        assert window._offline_report_training._training_jobs.config.backend == LOCAL_BACKEND
        assert not (tmp_path / "training-data").exists()
    finally:
        window.close()


def test_optional_trainer_refuses_unapproved_backend_before_any_torch_import(tmp_path):
    dataset = VerifiedOfflineDataset(
        tmp_path, 6, "test-dataset",
        ("normal", "thermal_hotspot_candidate"),
        ("train", "validation", "test"), "test-fingerprint",
    )
    config = OfflineTrainerConfiguration(
        backend="remote-commercial-ai", backend_version="v1",
        model_weights=tmp_path / "missing.pt", model_sha256="0" * 64,
        weights_license_review="unknown", epochs=1, seed=0,
    )
    with pytest.raises(PermissionError, match="explicit local"):
        local_resnet18_trainer(dataset, config, tmp_path, lambda x: None, Event())


def test_source_contract_has_no_weights_download_or_pickle_fallback():
    import inspect
    from mcm_solarcheck.services import offline_torchvision_classifier
    source = inspect.getsource(offline_torchvision_classifier)
    assert source.count("models.resnet18(weights=None") == 2
    assert "weights_only=True" in source
    assert "load_state_dict_from_url(" not in source
    assert "torch.hub." not in source
    assert "requests.get(" not in source
