"""Explicit local copy of approved YOLO files; no training or network actions."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat

from mcm_solarcheck.services.pv_dataset_intake import PublicDatasetRecord
from mcm_solarcheck.services.pv_training_approval_gate import require_matching_training_approval
from mcm_solarcheck.services.pv_training_approval_snapshot import TrainingApprovalSnapshot
from mcm_solarcheck.services.pv_training_dataset_fingerprint import fingerprint_local_yolo_dataset
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping


@dataclass(frozen=True)
class LocalTrainingStage:
    directory: Path
    dataset_sha256: str
    file_count: int
    total_bytes: int
    status: str = "staged_no_training"


def stage_approved_local_yolo_dataset(
    source: Path, destination: Path, record: PublicDatasetRecord,
    mapping: YoloClassMapping, site_by_image: dict[str, str],
    approval: TrainingApprovalSnapshot, *,
    max_files: int = 3000, max_total_bytes: int = 500_000_000,
    max_file_bytes: int = 30_000_000,
) -> LocalTrainingStage:
    """Create a new local destination and clean it up on any copy/verification error."""
    if type(max_files) is not int or not 6 <= max_files <= 100000:
        raise ValueError("invalid file count cap")
    if type(max_total_bytes) is not int or not 1 <= max_total_bytes <= 10_000_000_000:
        raise ValueError("invalid total byte cap")
    if type(max_file_bytes) is not int or not 1 <= max_file_bytes <= 1_000_000_000:
        raise ValueError("invalid per-file byte cap")
    source, destination = Path(source), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("staging destination already exists")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("regular destination parent required")
    source_real = source.resolve(strict=True)
    destination_real = destination.parent.resolve(strict=True) / destination.name
    if source_real == destination_real or source_real in destination_real.parents:
        raise ValueError("destination cannot be inside source")
    require_matching_training_approval(source, record, mapping, site_by_image, approval)
    before = fingerprint_local_yolo_dataset(source, max_files=max_files,
                                            max_total_bytes=max_total_bytes)
    if before.digest_sha256 != approval.dataset_sha256:
        raise PermissionError("approved fingerprint mismatch")
    created = False
    try:
        destination.mkdir(mode=0o700)
        created = True
        total = count = 0
        for kind, extensions in (("images", {".jpg", ".jpeg", ".png"}), ("labels", {".txt"})):
            for split in ("train", "val", "test"):
                src_folder = source / kind / split
                if src_folder.is_symlink() or not src_folder.is_dir():
                    raise ValueError("invalid source split")
                dst_folder = destination / kind / split
                dst_folder.mkdir(parents=True, mode=0o700)
                for path in sorted(src_folder.iterdir()):
                    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in extensions:
                        raise ValueError("invalid source file")
                    count += 1
                    size = path.stat().st_size
                    total += size
                    if count > max_files or size > max_file_bytes or total > max_total_bytes:
                        raise ValueError("staging size limit exceeded")
                    target = dst_folder / path.name
                    # O_NOFOLLOW rejects symlink replacement at open on supporting platforms.
                    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    fd = os.open(path, flags)
                    try:
                        if not stat.S_ISREG(os.fstat(fd).st_mode):
                            raise ValueError("source changed to nonregular file")
                        with os.fdopen(fd, "rb", closefd=False) as src, target.open("xb") as dst:
                            while chunk := src.read(1024 * 1024):
                                dst.write(chunk)
                    finally:
                        os.close(fd)
                    target.chmod(0o400)
        staged = fingerprint_local_yolo_dataset(destination, max_files=max_files,
                                                 max_total_bytes=max_total_bytes)
        after = fingerprint_local_yolo_dataset(source, max_files=max_files,
                                                max_total_bytes=max_total_bytes)
        if staged != before or after != before:
            raise ValueError("source or staged dataset changed during copy")
        for kind in ("images", "labels"):
            for split in ("train", "val", "test"):
                (destination / kind / split).chmod(0o500)
            (destination / kind).chmod(0o500)
        destination.chmod(0o500)
        return LocalTrainingStage(destination, staged.digest_sha256,
                                  staged.file_count, staged.total_bytes)
    except BaseException:
        if created:
            for parent, dirs, files in os.walk(destination):
                for name in files:
                    (Path(parent) / name).chmod(0o600)
                for name in dirs:
                    (Path(parent) / name).chmod(0o700)
            destination.chmod(0o700)
            shutil.rmtree(destination)
        raise
