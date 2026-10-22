"""Read-only local post-import acceptance of private DJI M3T original ZIPs.

No database initialization, migrations, project writes, uploads, or approval.
Return aggregate diagnostics only; filenames, capture times, GPS and file
paths must never appear in CLI output.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from zipfile import ZipFile

from mcm_solarcheck.importers.m3t_original_archive_audit import OriginalM3TArchiveAudit


def _digest(stream) -> str:
    digest = sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def verify_imported_originals(
    database_path: str | Path,
    project_id: str,
    audit: OriginalM3TArchiveAudit,
    thermal_zip: str | Path,
    rgb_zip: str | Path,
    *,
    include_unpaired_thermal: bool = False,
) -> dict:
    """Verify original provenance, exact copied bytes, and persisted frame counts.

    Metadata pair identity is deliberately not treated as validated geometry.
    The SQLite file is opened in mode=ro; no ProjectDatabase.initialize().
    This method reads only the single explicitly selected project.
    """
    if type(include_unpaired_thermal) is not bool:
        raise TypeError("explicit Boolean for unpaired thermal required")
    if not project_id or not project_id.strip():
        raise ValueError("existing project identifier required")
    db_path = Path(database_path)
    if not db_path.is_absolute() or not _regular_file(db_path):
        raise PermissionError("existing absolute regular database required")
    root = db_path.parent / "private-m3t-originals"
    if root.is_symlink() or not root.is_dir():
        raise PermissionError("private local original directory unavailable")

    accepted_thermal = set(audit.paired_sequences)
    if include_unpaired_thermal:
        accepted_thermal.update(audit.thermal_only_sequences)
    expected_t = {item.name: item for item in audit.thermal if item.sequence in accepted_thermal}
    expected_v = {item.name: item for item in audit.rgb}
    expected = {**expected_t, **expected_v}
    if len(expected) != len(expected_t) + len(expected_v):
        raise ValueError("ambiguous original file identity")

    # SQLite URI read-only mode permits WAL-backed desktop databases without
    # accidental initialization or schema migration.
    with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as conn:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("SELECT 1 FROM projects WHERE project_id=?", (project_id,)).fetchone() is None:
            raise KeyError("project not found")
        rgb_paths = [row[0] for row in conn.execute(
            "SELECT source_file FROM image_frames WHERE project_id=?", (project_id,)
        )]
        thermal_paths = [row[0] for row in conn.execute(
            "SELECT source_file FROM thermal_frames WHERE project_id=?", (project_id,)
        )]
        pair_count = int(conn.execute(
            "SELECT COUNT(*) FROM image_pairs WHERE project_id=?", (project_id,)
        ).fetchone()[0])

    if len(rgb_paths) != len(expected_v) or len(thermal_paths) != len(expected_t):
        raise ValueError("persisted frame counts differ from selected original ZIPs")
    if not (0 <= pair_count <= len(audit.paired_sequences)):
        raise ValueError("invalid stored pair count")

    seen: set[str] = set()
    selected_folder = None
    for raw_path, expected_modality in (
        *((p, "V") for p in rgb_paths),
        *((p, "T") for p in thermal_paths),
    ):
        source = Path(raw_path)
        if (not source.is_absolute() or not _regular_file(source)
                or source.parent.is_symlink()
                or source.parent.parent != root
                or source.name not in expected
                or expected[source.name].modality != expected_modality
                or source.name in seen):
            raise ValueError("untrusted or mismatched persisted source")
        if selected_folder is None:
            selected_folder = source.parent
        elif source.parent != selected_folder:
            raise ValueError("originals from multiple staging folders")
        seen.add(source.name)
    if seen != set(expected) or selected_folder is None:
        raise ValueError("persisted sources incomplete")

    manifest_path = selected_folder / "m3t-original-provenance.json"
    if not _regular_file(manifest_path) or manifest_path.stat().st_size > 2_000_000:
        raise ValueError("private provenance manifest missing or oversized")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("schema") != 1
            or manifest.get("status") != "private_originals_not_report_or_training_approved"
            or manifest.get("staged_thermal") != len(expected_t)
            or manifest.get("staged_rgb") != len(expected_v)
            or manifest.get("matched_pairs") != len(audit.paired_sequences)):
        raise ValueError("untrusted provenance manifest")

    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError("manifest file count mismatch")
    by_name: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("filename"), str):
            raise ValueError("invalid provenance entry")
        name = record["filename"]
        if (name not in expected or name in by_name
                or record.get("modality") != expected[name].modality
                or record.get("bytes") != expected[name].size_bytes
                or record.get("human_reviewed") is not False
                or record.get("training_rights_approved") is not False):
            raise ValueError("invalid provenance identity or permissions")
        by_name[name] = record
    if set(by_name) != set(expected):
        raise ValueError("manifest originals incomplete")

    # Compare the exact retained bytes with both signed-off staging hashes
    # and the still-private ZIP members. Never emit filenames or hashes.
    with ZipFile(thermal_zip) as thermal_archive, ZipFile(rgb_zip) as rgb_archive:
        for name, item in expected.items():
            stored = selected_folder / name
            if not _regular_file(stored) or stored.stat().st_size != item.size_bytes:
                raise ValueError("staged original missing or changed")
            with stored.open("rb") as stream:
                stored_hash = _digest(stream)
            archive = thermal_archive if item.modality == "T" else rgb_archive
            with archive.open(name) as stream:
                archive_hash = _digest(stream)
            if stored_hash != archive_hash or stored_hash != by_name[name].get("sha256"):
                raise ValueError("original byte integrity mismatch")

    return {
        "read_only_verification": True,
        "persistent_rgb_images": len(rgb_paths),
        "persistent_thermal_images": len(thermal_paths),
        "persistent_analysis_pair_records": pair_count,
        "filename_timestamp_matched_pairs": len(audit.paired_sequences),
        "analysis_pair_review_required": pair_count != len(audit.paired_sequences),
        "verified_original_copies": len(expected),
        "archive_and_provenance_sha256_agree": True,
        "radiometric_celsius_validated": False,
        "physical_module_identity_validated": False,
        "report_or_training_approved": False,
    }
