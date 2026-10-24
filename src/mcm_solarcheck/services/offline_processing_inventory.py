"""Private SQLite-bound processing-input inventory, not a finished analysis.

An inventory digest detects changes to imported evidence *stored in SQLite*.
It never attests that an external original file is still byte-identical.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class OfflineProcessingInventory:
    project_id: str
    rgb_frames: int
    thermal_frames: int
    image_pairs: int
    fingerprint: str

    @property
    def can_plan_processing(self) -> bool:
        # The thermal workflow is valid even if the camera has no RGB partner.
        return self.thermal_frames > 0

    @property
    def expected_thermal_work(self) -> int:
        return self.thermal_frames


# Only imported inputs. Findings/modules/reviews are processing outputs;
# including them would invalidate a run as it produces its own results.
_INPUT_TABLES = (
    ("image_frames", (
        "frame_id", "source_file", "timestamp_utc", "camera_make",
        "camera_model", "width", "height", "metadata_json",
    ), "frame_id"),
    ("thermal_frames", (
        "frame_id", "source_file", "timestamp_utc", "camera_make",
        "camera_model", "width", "height", "thermal_source", "metadata_json",
    ), "frame_id"),
    ("image_pairs", (
        "pair_id", "rgb_frame_id", "thermal_frame_id", "confidence",
        "method", "distance_m", "time_delta_s",
    ), "pair_id"),
    ("training_samples", (
        "source_frame_id", "modality", "content_sha256", "source_file",
    ), "modality, source_frame_id"),
)


def capture_offline_processing_inventory(database, project_id: str) -> OfflineProcessingInventory:
    """Fingerprint persisted project inputs only, with no external file reads.

    Project identifiers and paths are fed only into a private SHA-256 context;
    no customer paths, GPS or filenames are placed in return values or logs.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("existing project ID is required")
    digest = sha256()
    counts: dict[str, int] = {}
    with database.connect() as sql:
        if sql.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,),
        ).fetchone() is None:
            raise KeyError("Unknown project")
        digest.update(b"mcm-offline-processing-input-v1\n")
        digest.update(project_id.encode("utf-8"))
        digest.update(b"\n")
        for table, columns, ordering in _INPUT_TABLES:
            digest.update(table.encode("ascii") + b"\n")
            field_list = ", ".join(columns)
            cursor = sql.execute(
                f"SELECT {field_list} FROM {table} WHERE project_id=? "
                f"ORDER BY {ordering}", (project_id,),
            )
            count = 0
            for row in cursor:
                values = tuple(row)
                digest.update(json.dumps(
                    values, ensure_ascii=True, separators=(",", ":"),
                ).encode("utf-8") + b"\n")
                count += 1
            counts[table] = count
    return OfflineProcessingInventory(
        project_id=project_id,
        rgb_frames=counts["image_frames"],
        thermal_frames=counts["thermal_frames"],
        image_pairs=counts["image_pairs"],
        fingerprint=digest.hexdigest(),
    )
