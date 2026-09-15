"""Read-only inspection queries for review screens and reporting.

The query layer deliberately distinguishes calibrated Celsius evidence from raw
sensor values. Missing calibration is represented as ``None`` and is never
silently converted or estimated.
"""
from __future__ import annotations

from dataclasses import dataclass

from .sqlite import ProjectDatabase


@dataclass(frozen=True)
class InspectionSummary:
    project_id: str
    rgb_frames: int
    thermal_frames: int
    image_pairs: int
    pv_modules: int
    findings: int
    unreviewed_findings: int
    confirmed_findings: int
    rejected_findings: int
    unclear_findings: int
    calibrated_findings: int


@dataclass(frozen=True)
class FindingRecord:
    finding_id: str
    thermal_frame_id: str
    module_id: str | None
    pixel_x: int
    pixel_y: int
    finding_type: str
    confidence: float | None
    raw_value: int | None
    raw_delta_from_median: float | None
    temperature_c: float | None
    reviewer_status: str
    latitude: float | None
    longitude: float | None
    altitude_m: float | None


class InspectionQueries:
    """Stable read boundary between SQLite and UI/report generation."""

    def __init__(self, database: ProjectDatabase) -> None:
        self.database = database

    def summary(self, project_id: str) -> InspectionSummary:
        with self.database.connect() as db:
            project = db.execute(
                "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
            if project is None:
                raise KeyError(f"Unknown project: {project_id}")

            def count(table: str) -> int:
                return int(db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE project_id=?", (project_id,)
                ).fetchone()[0])

            statuses = {
                row["reviewer_status"]: int(row["n"])
                for row in db.execute(
                    """SELECT reviewer_status, COUNT(*) AS n
                       FROM findings WHERE project_id=? GROUP BY reviewer_status""",
                    (project_id,),
                )
            }
            calibrated = int(db.execute(
                "SELECT COUNT(*) FROM findings WHERE project_id=? AND temperature_c IS NOT NULL",
                (project_id,),
            ).fetchone()[0])

            return InspectionSummary(
                project_id=project_id,
                rgb_frames=count("image_frames"),
                thermal_frames=count("thermal_frames"),
                image_pairs=count("image_pairs"),
                pv_modules=count("pv_modules"),
                findings=count("findings"),
                unreviewed_findings=statuses.get("unreviewed", 0),
                confirmed_findings=statuses.get("confirmed", 0),
                rejected_findings=statuses.get("rejected", 0),
                unclear_findings=statuses.get("unclear", 0),
                calibrated_findings=calibrated,
            )

    def findings(
        self,
        project_id: str,
        *,
        reviewer_status: str | None = None,
        confirmed_only: bool = False,
    ) -> tuple[FindingRecord, ...]:
        if confirmed_only and reviewer_status is not None:
            raise ValueError("Use either confirmed_only or reviewer_status, not both")
        status = "confirmed" if confirmed_only else reviewer_status
        sql = """SELECT finding_id, thermal_frame_id, module_id, pixel_x, pixel_y,
                        finding_type, confidence, raw_value, raw_delta_from_median,
                        temperature_c, reviewer_status, latitude, longitude, altitude_m
                 FROM findings WHERE project_id=?"""
        params: list[object] = [project_id]
        if status is not None:
            sql += " AND reviewer_status=?"
            params.append(status)
        sql += " ORDER BY thermal_frame_id, pixel_y, pixel_x, finding_id"
        with self.database.connect() as db:
            rows = db.execute(sql, tuple(params)).fetchall()
        return tuple(FindingRecord(**dict(row)) for row in rows)
