"""Explicit, local-only provenance boundary for permissively licensed AI work.

A manifest is integrity/provenance evidence, NOT legal verification or a
cryptographic signature. The first trainer accepts only checkpoints freshly
initialized locally by this application; downloaded weights are NOT admitted.
No torch/torchvision import occurs on normal SolarCheck desktop startup.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

LOCAL_BACKEND = "torchvision-resnet18-local-init"
LOCAL_ARCHITECTURE = "torchvision.resnet18"
LOCAL_INIT = "weights=None; local random initialization"
LOCAL_MANIFEST_SCHEMA = 1
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"[0-9A-Za-z.+_\-]{1,80}\Z")


@dataclass(frozen=True)
class LocalCheckpointProvenance:
    weights_sha256: str
    torch_version: str
    torchvision_version: str
    class_count: int
    seed: int

    def __post_init__(self) -> None:
        if not isinstance(self.weights_sha256, str) or not _HEX.fullmatch(self.weights_sha256):
            raise ValueError("checkpoint hash must be lower-case SHA-256")
        for value in (self.torch_version, self.torchvision_version):
            if not isinstance(value, str) or not _VERSION.fullmatch(value):
                raise ValueError("explicit installed library version required")
        if type(self.class_count) is not int or not 2 <= self.class_count <= 100:
            raise ValueError("reviewed classification class count required")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("valid local initialization seed required")


def manifest_path(checkpoint: Path) -> Path:
    if not isinstance(checkpoint, Path) or not checkpoint.is_absolute():
        raise ValueError("absolute local checkpoint path required")
    if checkpoint.suffix.lower() != ".pt":
        raise ValueError("local model checkpoint must have .pt suffix")
    return checkpoint.with_suffix(".provenance.json")


def digest_file(path: Path, *, max_bytes: int = 500_000_000) -> str:
    if path.is_symlink() or not path.is_file():
        raise PermissionError("local checkpoint must be a regular file")
    size = path.stat().st_size
    if not 0 < size <= max_bytes:
        raise ValueError("local checkpoint size outside safe limits")
    sha = sha256()
    total = 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            total += len(block)
            if total > max_bytes:
                raise ValueError("local checkpoint changed size during verification")
            sha.update(block)
    if total != size:
        raise ValueError("local checkpoint changed during verification")
    return sha.hexdigest()


def encode_provenance(provenance: LocalCheckpointProvenance) -> bytes:
    payload = {
        "schema": LOCAL_MANIFEST_SCHEMA,
        "backend": LOCAL_BACKEND,
        "architecture": LOCAL_ARCHITECTURE,
        "initialization": LOCAL_INIT,
        "weights_sha256": provenance.weights_sha256,
        "torch_version": provenance.torch_version,
        "torchvision_version": provenance.torchvision_version,
        "class_count": provenance.class_count,
        "seed": provenance.seed,
        "upstream_license_review": "BSD-3-Clause project licensing; audit actual wheel components",
        "weights_origin": "generated on this PC without pre-trained weights",
    }
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


def verify_local_checkpoint(
    checkpoint: Path, *, expected_sha256: str | None = None,
    class_count: int | None = None,
) -> LocalCheckpointProvenance:
    """Reject downloaded/unknown checkpoints without a matching local manifest.

    The provenance manifest may be edited along with the file. It is NOT an
    authenticity signature. Only use checkpoints from a trusted local workspace.
    """
    location = manifest_path(checkpoint)
    if location.is_symlink() or not location.is_file() or location.stat().st_size > 4096:
        raise PermissionError("approved local provenance manifest required")
    try:
        raw = json.loads(location.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid model provenance") from exc
    if not isinstance(raw, dict) or set(raw) != {
        "schema", "backend", "architecture", "initialization", "weights_sha256",
        "torch_version", "torchvision_version", "class_count", "seed",
        "upstream_license_review", "weights_origin",
    }:
        raise PermissionError("unrecognized local model provenance")
    if (raw["schema"] != LOCAL_MANIFEST_SCHEMA or raw["backend"] != LOCAL_BACKEND
            or raw["architecture"] != LOCAL_ARCHITECTURE
            or raw["initialization"] != LOCAL_INIT
            or raw["weights_origin"] != "generated on this PC without pre-trained weights"
            or raw["upstream_license_review"] !=
            "BSD-3-Clause project licensing; audit actual wheel components"):
        raise PermissionError("only freshly initialized local OSS models permitted")
    evidence = LocalCheckpointProvenance(
        raw["weights_sha256"], raw["torch_version"], raw["torchvision_version"],
        raw["class_count"], raw["seed"],
    )
    if class_count is not None and evidence.class_count != class_count:
        raise PermissionError("checkpoint class count differs from reviewed dataset")
    actual = digest_file(checkpoint)
    if actual != evidence.weights_sha256 or (
        expected_sha256 is not None and actual != expected_sha256
    ):
        raise PermissionError("checkpoint is different from locally recorded bytes")
    return evidence
