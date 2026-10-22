"""Read-only post-import verification for individually selected DJI originals.

No SQL writes or schema migration, no ZIP dependency, no GPS/EXIF logging,
no release of findings, temperature claims, model training, or report.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from mcm_solarcheck.importers.m3t_original_files_audit import OriginalFilesAudit


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_original_file_project(
    database_path: str | Path,
    project_id: str,
    audit: OriginalFilesAudit,
) -> dict:
    """Ensure persisted project files are identical to selected originals.

    This validates only provenance, copies and row counts, not image analysis,
    real-world module identity or geometric registration.
    """
    if not isinstance(audit, OriginalFilesAudit):
        raise TypeError("An actual read-only original-file audit is required")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("An existing project ID is required")
    database = Path(database_path)
    if not database.is_absolute() or database.is_symlink() or not database.is_file():
        raise PermissionError("Existing absolute SQLite file required")
    root = database.parent / "private-m3t-originals"
    if root.is_symlink() or not root.is_dir():
        raise PermissionError("Private original-image store unavailable")
    expected = {item.name: item for item in audit.files}
    if len(expected) != len(audit.files):
        raise ValueError("Repeated source filenames are not accepted")
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone() is None:
            raise KeyError("Chosen project not present")
        rgb = [row[0] for row in conn.execute(
            "SELECT source_file FROM image_frames WHERE project_id=?", (project_id,)
        )]
        thermal = [row[0] for row in conn.execute(
            "SELECT source_file FROM thermal_frames WHERE project_id=?", (project_id,)
        )]
        pairs = int(conn.execute(
            "SELECT COUNT(*) FROM image_pairs WHERE project_id=?", (project_id,)
        ).fetchone()[0])
    if (len(rgb) != audit.rgb_images or len(thermal) != audit.thermal_images
            or not 0 <= pairs <= audit.matched_pairs):
        raise ValueError("Project frame counts or pair counts disagree with source set")

    seen: set[str] = set()
    staged_folder = None
    for raw, modality in ((*[(p, "V") for p in rgb], *[(p, "T") for p in thermal])):
        path = Path(raw)
        item = expected.get(path.name)
        if (not path.is_absolute() or path.is_symlink() or not path.is_file()
                or path.parent.is_symlink() or path.parent.parent != root
                or item is None or item.modality != modality
                or path.name in seen):
            raise ValueError("Untrusted or mismatched original source path in project")
        if staged_folder is None:
            staged_folder = path.parent
        elif path.parent != staged_folder:
            raise ValueError("Project originals must belong to one private copy batch")
        seen.add(path.name)
    if not seen or seen != set(expected) or staged_folder is None:
        raise ValueError("Incomplete imported original image set")

    manifest_path = staged_folder / "m3t-original-provenance.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or manifest_path.stat().st_size > 2_000_000):
        raise ValueError("Missing or oversized private original provenance")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("schema") != 1
            or manifest.get("input_mode") != "selected_original_files"
            or manifest.get("status") != "private_originals_not_report_or_training_approved"
            or manifest.get("staged_thermal") != audit.thermal_images
            or manifest.get("staged_rgb") != audit.rgb_images
            or manifest.get("matched_pairs") != audit.matched_pairs
            or manifest.get("unpaired_thermal_explicitly_staged") != audit.thermal_only):
        raise ValueError("Private provenance counters disagree with audited originals")

    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError("Private provenance listing is incomplete")
    by_name: dict[str, dict] = {}
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get("filename"), str):
            raise ValueError("Malformed private provenance file entry")
        name = row["filename"]
        item = expected.get(name)
        if (item is None or name in by_name
                or row.get("modality") != item.modality
                or row.get("sequence") != item.sequence
                or row.get("bytes") != item.size_bytes
                or row.get("human_reviewed") is not False
                or row.get("training_rights_approved") is not False):
            raise ValueError("Private provenance image identity or rights disagree")
        by_name[name] = row
    if set(by_name) != set(expected):
        raise ValueError("Manifest does not list exactly the imported originals")

    # Compare bytes with both original input files and manifest. Nothing here
    # mutates or publishes images, and no digest or path enters the result.
    for name, item in expected.items():
        stored = staged_folder / name
        if (stored.is_symlink() or not stored.is_file()
                or stored.stat().st_size != item.size_bytes
                or item.path.stat().st_size != item.size_bytes):
            raise ValueError("A selected original or stored copy changed")
        copied_hash = _sha256(stored)
        if copied_hash != _sha256(item.path) or copied_hash != by_name[name].get("sha256"):
            raise ValueError("Original image bytes or provenance digest mismatch")

    return {
        "read_only_verification": True,
        "persistent_rgb_images": len(rgb),
        "persistent_thermal_images": len(thermal),
        "persistent_analysis_pair_records": pairs,
        "filename_timestamp_matched_pairs": audit.matched_pairs,
        "analysis_pair_review_required": pairs != audit.matched_pairs,
        "verified_original_copies": len(expected),
        "source_copies_and_provenance_sha256_agree": True,
        "radiometric_celsius_validated": False,
        "physical_module_identity_validated": False,
        "report_or_training_approved": False,
    }
