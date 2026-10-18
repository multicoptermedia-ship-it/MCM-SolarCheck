"""Read-only diagnostics for interrupted JPEG-to-RGB array conversions.

Never clean up or modify customer files automatically.
"""
from pathlib import Path


def inspect_rgb_array_staging(directory):
    """Report leftover converter staging files, without opening or changing them."""
    folder = Path(directory)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("regular RGB working directory required")
    staging = []
    for path in folder.iterdir():
        if path.is_symlink():
            raise ValueError("symlink in RGB working directory")
        if path.name.startswith(".rgb-array-") and path.name.endswith(".tmp"):
            if not path.is_file():
                raise ValueError("non-file RGB staging entry")
            staging.append({"name": path.name, "size_bytes": path.stat().st_size})
    staging.sort(key=lambda item: item["name"])
    return {
        "staging_files": staging,
        "requires_manual_review": bool(staging),
        "read_only": True,
    }
