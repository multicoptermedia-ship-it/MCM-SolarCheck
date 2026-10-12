"""Stable local SHA-256 manifest for audited YOLO datasets; never copies images."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class DatasetFingerprint:
    digest_sha256: str
    file_count: int
    total_bytes: int


def fingerprint_local_yolo_dataset(root: Path, *, max_files: int = 3000,
                                   max_total_bytes: int = 500_000_000) -> DatasetFingerprint:
    if type(max_files) is not int or max_files < 1 or type(max_total_bytes) is not int or max_total_bytes < 1:
        raise ValueError("positive fingerprint limits required")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("regular dataset root required")
    digest = sha256()
    count = total = 0
    for kind, extensions in (("images", {".jpg", ".jpeg", ".png"}), ("labels", {".txt"})):
        for split in ("train", "val", "test"):
            folder = root / kind / split
            if folder.is_symlink() or not folder.is_dir():
                raise ValueError("required dataset split missing")
            entries = sorted(folder.iterdir(), key=lambda p: p.name)
            count += len(entries)
            if count > max_files:
                raise ValueError("dataset file count exceeds limit")
            for path in entries:
                if path.is_symlink() or not path.is_file() or path.suffix.lower() not in extensions:
                    raise ValueError("unexpected or linked dataset file")
                relative = path.relative_to(root).as_posix().encode("utf-8")
                digest.update(len(relative).to_bytes(4, "big"))
                digest.update(relative)
                size = path.stat().st_size
                total += size
                if total > max_total_bytes:
                    raise ValueError("dataset bytes exceed limit")
                content_hash = sha256()
                with path.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        content_hash.update(chunk)
                digest.update(content_hash.digest())
    return DatasetFingerprint(digest.hexdigest(), count, total)
