"""Portable, network-free wheelhouse integrity and target-compatibility checks.

The manifest is a local checksum inventory, NOT a signature, trusted lockfile,
license clearance or malware/security scan. Build wheels on a matching system.
No package manager or network access occurs in this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

MANIFEST = "wheelhouse-manifest.json"
_SCHEMA = 1
_NAME = re.compile(r"[A-Za-z0-9_.+\-]+\.whl\Z")
_MAX_WHEELS = 1000
_MAX_MANIFEST = 200_000


def _target() -> str:
    return f"{sys.platform}-{platform.machine().lower()}-cp{sys.version_info.major}{sys.version_info.minor}"


def _safe_dir(path: Path) -> Path:
    if not path.is_absolute() or not path.is_dir() or path.is_symlink():
        raise ValueError("existing absolute wheelhouse directory required")
    return path


def _safe_requirements(path: Path) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("existing absolute requirements file required")
    if not 0 < path.stat().st_size <= 100_000:
        raise ValueError("invalid requirements size")
    return path.read_bytes()


def _digest(path: Path) -> tuple[int, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("wheel must be a regular non-linked file")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("wheel is empty")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha.update(block)
    if path.stat().st_size != size:
        raise ValueError("wheel changed during hashing")
    return size, sha.hexdigest()


def _wheel_files(root: Path) -> list[Path]:
    result = []
    for path in root.iterdir():
        if path.name == MANIFEST:
            continue
        if not _NAME.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            raise ValueError("wheelhouse contains non-wheel, symlink or unsafe name")
        result.append(path)
    if not 0 < len(result) <= _MAX_WHEELS:
        raise ValueError("wheelhouse must contain 1-1000 wheels")
    return sorted(result, key=lambda p: p.name)


def create_manifest(wheelhouse: str | Path, requirements: str | Path) -> Path:
    """Record wheel SHA256 plus exact requirements and interpreter target."""
    root = _safe_dir(Path(wheelhouse))
    req = _safe_requirements(Path(requirements))
    files = _wheel_files(root)
    inventory = [
        {"name": file.name, "size": size, "sha256": digest}
        for file in files
        for size, digest in [_digest(file)]
    ]
    payload = {
        "schema": _SCHEMA,
        "target": _target(),
        "requirements_sha256": hashlib.sha256(req).hexdigest(),
        "wheels": inventory,
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    # A manifest already published cannot be replaced by accident. An
    # intentional rebuild must clear the old manifest before refreshing wheels.
    destination = root / MANIFEST
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("wheelhouse manifest already exists")
    fd, staged = tempfile.mkstemp(prefix=".wheelhouse-", dir=root)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        # Atomic exclusive publication: no overwriting an existing manifest.
        try:
            os.link(staged, destination)
        except FileExistsError:
            raise
    finally:
        Path(staged).unlink(missing_ok=True)
    return destination


def verify_manifest(wheelhouse: str | Path, requirements: str | Path) -> int:
    """Raise ValueError/PermissionError on any mismatch; return wheel count."""
    root = _safe_dir(Path(wheelhouse))
    req = _safe_requirements(Path(requirements))
    path = root / MANIFEST
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _MAX_MANIFEST:
        raise ValueError("wheelhouse manifest missing, linked or oversized")
    try:
        manifest = json.loads(path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid wheelhouse manifest") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema", "target", "requirements_sha256", "wheels",
    } or manifest["schema"] != _SCHEMA or manifest["target"] != _target():
        raise ValueError("wheelhouse does not match this Python/platform")
    if manifest["requirements_sha256"] != hashlib.sha256(req).hexdigest():
        raise ValueError("requirements differ from prepared wheelhouse")
    expected = manifest["wheels"]
    files = _wheel_files(root)
    if not isinstance(expected, list) or len(expected) != len(files):
        raise ValueError("wheelhouse wheel inventory mismatch")
    for item, file in zip(expected, files):
        if not isinstance(item, dict) or set(item) != {"name", "size", "sha256"}:
            raise ValueError("invalid wheel entry")
        size, sha = _digest(file)
        if item["name"] != file.name or item["size"] != size or item["sha256"] != sha:
            raise ValueError("wheelhouse wheel hash mismatch")
    return len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local offline Windows wheel inventory")
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--requirements", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            create_manifest(args.wheelhouse, args.requirements)
        else:
            verify_manifest(args.wheelhouse, args.requirements)
    except (OSError, ValueError, PermissionError) as exc:
        parser.exit(2, f"Wheelhouse not ready: {exc}\n")
    print(f"Wheelhouse {args.command}: OK for {_target()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
