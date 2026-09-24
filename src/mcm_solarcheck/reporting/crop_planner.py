"""Resolve report crop plans from persisted, sensor-specific geometry."""
from __future__ import annotations
from dataclasses import dataclass
import json
from .image_crop import CropBox, polygon_crop_box


@dataclass(frozen=True)
class ReportCropPlan:
    source_frame_id: str
    source_file: str
    modality: str
    box: CropBox
    geometry_source: str


def thermal_module_crop_plan(database, project_id: str, module_id: str, *, padding_fraction: float=0.12) -> ReportCropPlan | None:
    """Use only the module polygon stored for its own thermal frame."""
    with database.connect() as db:
        row=db.execute("""SELECT m.frame_id,m.polygon_json,t.source_file,t.width,t.height
            FROM pv_modules m JOIN thermal_frames t ON t.project_id=m.project_id AND t.frame_id=m.frame_id
            WHERE m.project_id=? AND m.module_id=?""",(project_id,module_id)).fetchone()
    if row is None or row["width"] is None or row["height"] is None: return None
    try: polygon=json.loads(row["polygon_json"])
    except (TypeError,json.JSONDecodeError): return None
    box=polygon_crop_box(polygon,int(row["width"]),int(row["height"]),padding_fraction=padding_fraction)
    return ReportCropPlan(row["frame_id"],row["source_file"],"thermal",box,"persisted_module_polygon")


def rgb_finding_crop_plan(database, project_id: str, finding_id: str, *, half_size_px: int=80) -> ReportCropPlan | None:
    """Crop RGB only around a validated persisted cross-sensor projection."""
    if isinstance(half_size_px,bool) or not isinstance(half_size_px,int) or half_size_px<=0:
        raise ValueError("half_size_px must be a positive integer")
    with database.connect() as db:
        row=db.execute("""SELECT l.rgb_frame_id,l.rgb_pixel_x,l.rgb_pixel_y,l.transform_method,
            l.transform_validated,i.source_file,i.width,i.height
            FROM finding_sensor_links l JOIN image_frames i
              ON i.project_id=l.project_id AND i.frame_id=l.rgb_frame_id
            WHERE l.project_id=? AND l.finding_id=?""",(project_id,finding_id)).fetchone()
    if row is None or not bool(row["transform_validated"]) or row["rgb_pixel_x"] is None or row["rgb_pixel_y"] is None or row["width"] is None or row["height"] is None:
        return None
    x=float(row["rgb_pixel_x"]); y=float(row["rgb_pixel_y"]); width=int(row["width"]); height=int(row["height"])
    left=max(0,int(x-half_size_px)); top=max(0,int(y-half_size_px))
    right=min(width,int(x+half_size_px)); bottom=min(height,int(y+half_size_px))
    if right<=left or bottom<=top: return None
    return ReportCropPlan(row["rgb_frame_id"],row["source_file"],"rgb",CropBox(left,top,right,bottom),f"validated_cross_sensor:{row['transform_method']}")
