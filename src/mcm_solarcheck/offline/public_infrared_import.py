"""Import the pinned Raptor Maps public infrared ZIP from a LOCAL file only.

Strictly separate from SolarCheck client DB, consent ledgers and production
models. The upstream archive has image-level labels but NO validated physical
site grouping. Exported data is EXPLORATORY ONLY, never automatically trainable
or report-ready. No network API and no data is stored in Git.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha1, sha256
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile

from PIL import Image

from mcm_solarcheck.services.pv_public_infrared_source import (
    ARCHIVE_GIT_BLOB_SHA1, ARCHIVE_NAME, ARCHIVE_SIZE, DATASET_ID, LICENSE_URL,
    MODALITY, ORIGINAL_CLASSES, REVIEW_LIMIT, SOURCE_URL, UPSTREAM_COMMIT,
    RaptorImportAuthorization,
)

_IMAGE_PATH = re.compile(r"images/[A-Za-z0-9_\-]+\.jpg\Z", re.IGNORECASE)
MAX_ZIP_ENTRIES = 22_000
MAX_UNPACKED_SIZE = 350_000_000
MAX_SAMPLE_BYTES = 2_000_000
MAX_METADATA_BYTES = 8_000_000


def _pinned_archive_identity(
    archive: Path, expected_blob_sha1: str, expected_size: int,
) -> str:
    if (not archive.is_absolute() or archive.is_symlink()
            or not archive.is_file() or archive.name != ARCHIVE_NAME):
        raise PermissionError("absolute, regular named upstream ZIP file required")
    size = archive.stat().st_size
    if size != expected_size:
        raise PermissionError("ZIP size differs from pinned upstream source")
    blob_sha = sha1(f"blob {size}\0".encode("ascii"))
    content_sha = sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            blob_sha.update(block)
            content_sha.update(block)
    if blob_sha.hexdigest() != expected_blob_sha1:
        raise PermissionError("ZIP does not match pinned Git blob, cannot ingest")
    return content_sha.hexdigest()


def _members(source: zipfile.ZipFile):
    archive = {}
    total = 0
    for info in source.infolist():
        if len(archive) >= MAX_ZIP_ENTRIES:
            raise ValueError("too many ZIP members")
        name = info.filename
        if (not isinstance(name, str) or not name or "\\" in name
                or name.startswith("/")
                or any(p in ("", ".", "..") for p in name.rstrip("/").split("/"))):
            raise PermissionError("unsafe ZIP path")
        kind = stat.S_IFMT(info.external_attr >> 16)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise PermissionError("symlink/special ZIP entries forbidden")
        if info.is_dir():
            continue
        if name in archive or info.file_size < 1:
            raise ValueError("duplicate or empty ZIP member")
        if info.compress_size > MAX_UNPACKED_SIZE:
            raise ValueError("oversized compressed ZIP member")
        total += info.file_size
        if total > MAX_UNPACKED_SIZE:
            raise ValueError("ZIP expands beyond limit")
        archive[name] = info
    candidates = [name for name in archive if name.endswith("module_metadata.json")]
    if len(candidates) != 1:
        raise ValueError("exactly one upstream module_metadata.json is required")
    name = candidates[0]
    root = name[: -len("module_metadata.json")]
    if root and not root.endswith("/"):
        raise PermissionError("unsafe upstream ZIP root")
    if not (len(root.split("/")) <= 3 and
            not any(p in (".", "..") for p in root.split("/") if p)):
        raise PermissionError("unexpected upstream ZIP root")
    if archive[name].file_size > MAX_METADATA_BYTES:
        raise ValueError("metadata manifest too large")
    return archive, root, name


def import_raptor_maps_zip(
    archive: Path, destination: Path, authorization: RaptorImportAuthorization,
    *, expected_blob_sha1: str = ARCHIVE_GIT_BLOB_SHA1,
    expected_size: int = ARCHIVE_SIZE,
) -> dict:
    """Publish only a fully verified, isolated research corpus.

    The expected hash/size overrides are exclusively for synthetic tests; the
    CLI always uses the pinned official source constants.
    """
    if not isinstance(authorization, RaptorImportAuthorization):
        raise PermissionError("documented explicit local dataset rights review required")
    if (not isinstance(destination, Path) or not destination.is_absolute()
            or destination.exists() or destination.is_symlink()
            or destination.parent.is_symlink() or not destination.parent.is_dir()):
        raise PermissionError("fresh absolute research destination in real directory required")
    archive_sha256 = _pinned_archive_identity(
        archive, expected_blob_sha1, expected_size,
    )
    with zipfile.ZipFile(archive, "r") as zipped:
        members, root, manifest_file = _members(zipped)
        try:
            metadata = json.loads(zipped.read(manifest_file))
        except (UnicodeError, ValueError) as exc:
            raise ValueError("invalid upstream metadata JSON") from exc
        if not isinstance(metadata, dict) or not 1 <= len(metadata) <= 20_100:
            raise ValueError("unexpected upstream record count")
        refs = {}
        counts = Counter()
        for source_id, details in metadata.items():
            if (not isinstance(source_id, str) or not re.fullmatch(r"[0-9A-Za-z_\-]{1,100}", source_id)
                    or not isinstance(details, dict)
                    or not isinstance(details.get("image_filepath"), str)
                    or details.get("anomaly_class") not in ORIGINAL_CLASSES):
                raise ValueError("unrecognized upstream image or class annotation")
            name = details["image_filepath"]
            if not _IMAGE_PATH.fullmatch(name):
                raise PermissionError("unexpected upstream image filepath")
            full_name = root + name
            if full_name not in members or full_name in refs:
                raise ValueError("image missing or duplicated by upstream metadata")
            if members[full_name].file_size > MAX_SAMPLE_BYTES:
                raise ValueError("individual image exceeds size cap")
            refs[full_name] = (source_id, name, details["anomaly_class"])
            counts[details["anomaly_class"]] += 1
        extras = set(members) - set(refs) - {manifest_file}
        if extras:
            raise PermissionError("unindexed file in public dataset archive")
        # Never publish some images if later ZIP members are corrupt.
        destination.mkdir(mode=0o700)
        try:
            images = destination / "images"
            images.mkdir(mode=0o700)
            rows = []
            for full_name, (source_id, name, label) in sorted(refs.items()):
                content = zipped.read(members[full_name])
                if not 0 < len(content) <= MAX_SAMPLE_BYTES:
                    raise ValueError("invalid image size")
                with Image.open(BytesIO(content)) as image:
                    image.verify()
                with Image.open(BytesIO(content)) as image:
                    if sorted(image.size) != [24, 40]:
                        raise ValueError("unexpected upstream IR image dimensions")
                    if image.format != "JPEG":
                        raise ValueError("only upstream JPEG images permitted")
                local_name = f"{source_id}.jpg"
                target = images / local_name
                if target.exists():
                    raise ValueError("duplicate source image ID")
                with target.open("xb") as stream:
                    stream.write(content)
                rows.append({
                    "source_id": source_id,
                    "image": "images/" + local_name,
                    "class": label,
                    "sha256": sha256(content).hexdigest(),
                })
            index = {
                "schema": 1, "dataset_id": DATASET_ID,
                "source_url": SOURCE_URL, "source_commit": UPSTREAM_COMMIT,
                "license_url": LICENSE_URL, "license_claim": "MIT in upstream repository",
                "reviewer": authorization.reviewer,
                "rights_evidence_reference": authorization.evidence_reference,
                "archive_git_blob_sha1": expected_blob_sha1,
                "archive_sha256": archive_sha256,
                "image_modality": MODALITY,
                "status": "exploratory_only_not_approved_for_reports",
                "site_grouping": "not_available_no_site_disjoint_validation",
                "limitations": REVIEW_LIMIT,
                "class_counts": dict(sorted(counts.items())),
                "samples": rows,
            }
            with (destination / "public-infrared-index.json").open(
                "x", encoding="utf-8",
            ) as stream:
                json.dump(index, stream, sort_keys=True, ensure_ascii=False)
                stream.write("\n")
            return {"images": len(rows), "counts": dict(sorted(counts.items())),
                    "sha256": archive_sha256, "index": str(destination / "public-infrared-index.json")}
        except BaseException:
            shutil.rmtree(destination, ignore_errors=True)
            raise


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Offline import of pinned Raptor Maps infrared benchmark, research-only",
    )
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--license-evidence", required=True)
    parser.add_argument(
        "--exploratory-only", action="store_true",
        help="Confirm that no report, commercial release, or model auto-deploy is permitted",
    )
    args = parser.parse_args(argv)
    try:
        approved = RaptorImportAuthorization(
            args.reviewer, args.license_evidence, args.exploratory_only,
        )
        result = import_raptor_maps_zip(args.archive, args.destination, approved)
    except (OSError, ValueError, PermissionError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Public infrared dataset import rejected: {exc}\n")
    print(
        f"Research-only infrared dataset imported locally: {result['images']} "
        "images; not radiometric, no site-safe validation and no model deployment."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
