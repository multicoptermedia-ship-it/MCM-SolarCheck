"""Cancellable read-only integrity scan used by the Windows worker."""
from pathlib import Path

from mcm_solarcheck.services.flight_rgb_batch_resume import inspect_rgb_batch_resume


class IntegrityScanCancelled(Exception):
    """The user cancelled before the next file was inspected."""


def scan_rgb_integrity(source_folder, output_folder, *, on_progress=None,
                       should_cancel=None):
    source = Path(source_folder)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("regular JPEG source folder required")
    images = sorted((p for p in source.iterdir()
                     if p.suffix.lower() in (".jpg", ".jpeg")),
                    key=lambda p: p.name.casefold())
    if not images:
        raise ValueError("no JPEG images in source folder")
    if len({p.stem.casefold() for p in images}) != len(images):
        raise ValueError("colliding RGB output names across JPEG sources")
    if any(p.is_symlink() or not p.is_file() for p in images):
        raise ValueError("regular JPEG files required")
    entries = []
    total = len(images)
    for index, image in enumerate(images, 1):
        if should_cancel is not None and should_cancel():
            raise IntegrityScanCancelled()
        result = inspect_rgb_batch_resume([image], output_folder)
        entries.extend(result["entries"])
        if on_progress is not None:
            on_progress(index, total, result["entries"][0]["status"])
    if should_cancel is not None and should_cancel():
        raise IntegrityScanCancelled()
    return {"entries": entries, "read_only": True,
            "safe_to_resume_automatically": False,
            "verified_outputs": sum(e["status"] == "verified_provenance" for e in entries),
            "existing_outputs_unverified_provenance": any(
                e["status"] == "existing_shape_valid" for e in entries)}
