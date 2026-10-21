"""Read-only, pinned public infrared ZIP structure inventory.

On research preparation machines the inventory reveals ZIP entries not covered
by upstream JSON, without extracting, mutating projects or authorizing training.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import zipfile

from mcm_solarcheck.offline.public_infrared_import import (
    _members, _pinned_archive_identity,
)
from mcm_solarcheck.services.pv_public_infrared_source import (
    ARCHIVE_GIT_BLOB_SHA1, ARCHIVE_SIZE,
)


def inspect_pinned_archive(
    archive: Path, *, expected_blob_sha1: str = ARCHIVE_GIT_BLOB_SHA1,
    expected_size: int = ARCHIVE_SIZE,
) -> dict:
    original_sha256 = _pinned_archive_identity(
        archive, expected_blob_sha1, expected_size,
    )
    with zipfile.ZipFile(archive) as zipped:
        members, root, manifest_file = _members(zipped)
        try:
            metadata = json.loads(zipped.read(manifest_file))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("invalid public module metadata") from exc
        if not isinstance(metadata, dict):
            raise ValueError("unexpected public metadata structure")
        referenced = set()
        labels = Counter()
        for entry in metadata.values():
            if not isinstance(entry, dict):
                raise ValueError("unexpected public metadata row")
            name = entry.get("image_filepath")
            if not isinstance(name, str):
                raise ValueError("missing public image path")
            referenced.add(root + name)
            labels[str(entry.get("anomaly_class"))] += 1
        extras = sorted(set(members) - referenced - {manifest_file})
        kinds = Counter(Path(x).suffix.lower() or "<none>" for x in extras)
        return {
            "archive_sha256": original_sha256,
            "archive_files": len(members),
            "metadata_images": len(metadata),
            "metadata_classes": dict(sorted(labels.items())),
            "unreferenced_file_count": len(extras),
            "unreferenced_extensions": dict(sorted(kinds.items())),
            "unreferenced_examples": extras[:12],
            "action": "inspection_only_no_images_extracted",
        }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Inspect pinned upstream infrared ZIP without extraction",
    )
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect_pinned_archive(args.archive)
    except (OSError, ValueError, PermissionError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Public ZIP inspection refused: {exc}\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
