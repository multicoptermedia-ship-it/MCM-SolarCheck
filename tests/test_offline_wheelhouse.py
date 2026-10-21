"""Wheelhouse checks must remain entirely local and fail closed."""
from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

from mcm_solarcheck.offline import wheelhouse


def prepare(tmp_path):
    root = tmp_path / "wheels"
    root.mkdir()
    req = tmp_path / "requirements.txt"
    req.write_text("examplepkg==1.0\n", encoding="utf-8")
    (root / "examplepkg-1.0-py3-none-any.whl").write_bytes(b"synthetic wheel bytes")
    return root, req


def test_creates_verifiable_inventory_without_network_or_secrets(tmp_path, monkeypatch):
    root, req = prepare(tmp_path)
    monkeypatch.setattr(
        socket, "create_connection",
        lambda *_a, **_kw: pytest.fail("unexpected network access"),
    )
    result = wheelhouse.create_manifest(root, req)
    assert result == root / wheelhouse.MANIFEST
    assert wheelhouse.verify_manifest(root, req) == 1
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["target"] == wheelhouse._target()
    assert len(payload["wheels"][0]["sha256"]) == 64
    assert payload["wheels"][0]["size"] == len(b"synthetic wheel bytes")
    assert set(payload) == {"schema", "target", "requirements_sha256", "wheels"}
    assert "password" not in result.read_text(encoding="utf-8")


@pytest.mark.parametrize("damage", [
    "requirements", "wheel", "extra", "missing", "manifest",
    "target", "name", "size", "sha", "schema",
])
def test_refuses_modifications_or_environment_mismatch(tmp_path, damage):
    root, req = prepare(tmp_path)
    wheelhouse.create_manifest(root, req)
    wheel = next(root.glob("*.whl"))
    manifest = root / wheelhouse.MANIFEST
    if damage == "requirements":
        req.write_text("examplepkg==1.1\n", encoding="utf-8")
    elif damage == "wheel":
        wheel.write_bytes(b"changed wheel bytes")
    elif damage == "extra":
        (root / "other-2.0-py3-none-any.whl").write_bytes(b"other bytes")
    elif damage == "missing":
        wheel.unlink()
    elif damage == "manifest":
        manifest.write_text("not JSON", encoding="utf-8")
    else:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if damage == "target":
            data["target"] = "win32-amd64-cp39"
        if damage == "name":
            data["wheels"][0]["name"] = "../escape.whl"
        if damage == "size":
            data["wheels"][0]["size"] = 100
        if damage == "sha":
            data["wheels"][0]["sha256"] = "0" * 64
        if damage == "schema":
            data["schema"] = 44
        manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        wheelhouse.verify_manifest(root, req)


def test_create_is_exclusive_and_wheelhouse_must_have_only_wheels(tmp_path):
    root, req = prepare(tmp_path)
    wheelhouse.create_manifest(root, req)
    before = (root / wheelhouse.MANIFEST).read_bytes()
    with pytest.raises(FileExistsError):
        wheelhouse.create_manifest(root, req)
    assert (root / wheelhouse.MANIFEST).read_bytes() == before
    (root / "unexpected.txt").write_text("irrelevant")
    with pytest.raises(ValueError):
        wheelhouse.verify_manifest(root, req)
    with pytest.raises(ValueError):
        wheelhouse.create_manifest(root, req)


def test_missing_or_empty_wheels_never_publish_manifest(tmp_path):
    root, req = prepare(tmp_path)
    list(root.glob("*.whl"))[0].unlink()
    with pytest.raises(ValueError):
        wheelhouse.create_manifest(root, req)
    assert not (root / wheelhouse.MANIFEST).exists()
    (root / "zero-1.0-py3-none-any.whl").touch()
    with pytest.raises(ValueError):
        wheelhouse.create_manifest(root, req)
    assert not (root / wheelhouse.MANIFEST).exists()


def test_symlink_and_unexpected_files_denied(tmp_path):
    root, req = prepare(tmp_path)
    invalid = root / "linked-1.0-py3-none-any.whl"
    try:
        invalid.symlink_to(next(root.glob("*.whl")))
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(ValueError):
        wheelhouse.create_manifest(root, req)
    invalid.unlink()
    manifest = wheelhouse.create_manifest(root, req)
    manifest.unlink()
    manifest.symlink_to(tmp_path / "target")
    with pytest.raises(ValueError):
        wheelhouse.verify_manifest(root, req)


def test_relative_paths_and_wrong_cli_action_denied(tmp_path, capsys):
    root, req = prepare(tmp_path)
    with pytest.raises(ValueError):
        wheelhouse.create_manifest("wheels", req)
    with pytest.raises(ValueError):
        wheelhouse.create_manifest(root, Path("requirements.txt"))
    assert wheelhouse.main([
        "create", "--wheelhouse", str(root), "--requirements", str(req),
    ]) == 0
    assert wheelhouse.main([
        "verify", "--wheelhouse", str(root), "--requirements", str(req),
    ]) == 0
    assert "OK" in capsys.readouterr().out


def test_readonly_verify_does_not_modify_wheel_inventory(tmp_path):
    root, req = prepare(tmp_path)
    wheelhouse.create_manifest(root, req)
    earlier = {x.name: x.read_bytes() for x in root.iterdir()}
    assert wheelhouse.verify_manifest(root, req) == 1
    assert earlier == {x.name: x.read_bytes() for x in root.iterdir()}
