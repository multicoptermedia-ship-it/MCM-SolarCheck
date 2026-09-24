"""Build derived report assets without modifying inspection source images."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .crop_planner import thermal_module_crop_plan, rgb_finding_crop_plan
from .image_materializer import materialize_crop


@dataclass(frozen=True)
class ReportAsset:
    path: Path
    source_frame_id: str
    modality: str
    geometry_source: str


def _safe_name(value: str) -> str:
    cleaned="".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)
    return cleaned or "asset"


def build_detail_assets(database, project_id: str, finding_id: str, module_id: str, output_dir: str | Path) -> tuple[ReportAsset,...]:
    """Create deterministic crops; RGB remains absent unless its transform was validated."""
    output=Path(output_dir); assets=[]
    thermal=thermal_module_crop_plan(database,project_id,module_id)
    rgb=rgb_finding_crop_plan(database,project_id,finding_id)
    for plan in (rgb,thermal):
        if plan is None: continue
        suffix=Path(plan.source_file).suffix.lower() or ".png"
        target=output/f"{_safe_name(module_id)}_{_safe_name(finding_id)}_{plan.modality}{suffix}"
        materialize_crop(plan.source_file,target,plan.box)
        assets.append(ReportAsset(target,plan.source_frame_id,plan.modality,plan.geometry_source))
    return tuple(assets)
