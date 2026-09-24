"""Reviewed spatial annotation contract for Phase 8 detector training."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ReviewedGeometry:
    """Human-reviewed pixel geometry tied to one source representation."""

    source_frame_id: str
    reviewer: str
    representation: str
    box_xyxy: tuple[float, float, float, float] | None = None
    polygon_px: tuple[tuple[float, float], ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_frame_id,str) or not self.source_frame_id.strip():
            raise ValueError("geometry source frame must not be empty")
        if not isinstance(self.reviewer,str) or not self.reviewer.strip():
            raise ValueError("geometry reviewer must not be empty")
        if self.representation not in {"rendered_rgb","grayscale_8bit"}:
            raise ValueError("geometry requires an explicit rendered representation")
        if self.box_xyxy is None and self.polygon_px is None:
            raise ValueError("reviewed geometry requires a box or polygon")
        if self.box_xyxy is not None:
            if len(self.box_xyxy) != 4:
                raise ValueError("geometry box must contain four coordinates")
            x1,y1,x2,y2=self.box_xyxy
            if not all(isfinite(float(v)) for v in self.box_xyxy) or x2 <= x1 or y2 <= y1:
                raise ValueError("geometry box must be finite with positive area")
        if self.polygon_px is not None:
            if len(self.polygon_px) < 3:
                raise ValueError("geometry polygon requires at least three points")
            for point in self.polygon_px:
                if len(point) != 2 or not all(isfinite(float(v)) for v in point):
                    raise ValueError("geometry polygon points must be finite x/y pairs")

    @property
    def task_support(self) -> frozenset[str]:
        tasks=set()
        if self.box_xyxy is not None:
            tasks.add("detection")
        if self.polygon_px is not None:
            tasks.add("segmentation")
        return frozenset(tasks)


def require_geometry_for_task(value: ReviewedGeometry, task: str) -> ReviewedGeometry:
    """Fail closed when reviewed geometry cannot support the requested trainer task."""
    if task not in {"detection","segmentation"}:
        raise ValueError("training geometry task must be detection or segmentation")
    if task not in value.task_support:
        raise ValueError(f"reviewed geometry does not support {task}")
    return value
