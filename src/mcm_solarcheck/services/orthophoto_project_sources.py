"""Read imported original image paths from a specific persisted project."""
from __future__ import annotations

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame


def project_imported_frames(database, project_id: str):
    """Read frame identity and dimensions; no synthetic camera geometry."""
    with database.connect() as db:
        if db.execute("SELECT 1 FROM projects WHERE project_id=?", (project_id,)).fetchone() is None:
            raise KeyError(f"Unknown project: {project_id}")
        rgb = db.execute(
            "SELECT frame_id,source_file,width,height FROM image_frames WHERE project_id=? ORDER BY frame_id",
            (project_id,),
        ).fetchall()
        thermal = db.execute(
            "SELECT frame_id,source_file,width,height FROM thermal_frames WHERE project_id=? ORDER BY frame_id",
            (project_id,),
        ).fetchall()
    from pathlib import Path
    return (
        tuple(ImageFrame(row["frame_id"], Path(row["source_file"]), width=row["width"], height=row["height"]) for row in rgb),
        tuple(ThermalFrame(row["frame_id"], Path(row["source_file"]), width=row["width"], height=row["height"]) for row in thermal),
    )
