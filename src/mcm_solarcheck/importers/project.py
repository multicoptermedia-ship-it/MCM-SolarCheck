"""Project-wide DJI M3T RGB/thermal import orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcm_solarcheck.domain.models import ImageFrame, ImagePair
from mcm_solarcheck.pairing.rgb_thermal import pair_rgb_thermal_frames
from .batch import M3TBatchResult, import_m3t_directory
from .m3t import M3TImporter
from .m3t_rgb import M3TRGBImporter


@dataclass(frozen=True)
class ProjectImportResult:
    rgb_frames: tuple[ImageFrame, ...]
    thermal_batch: M3TBatchResult
    pairs: tuple[ImagePair, ...]

    @property
    def unpaired_rgb_count(self) -> int:
        return len(self.rgb_frames) - len({p.rgb_frame_id for p in self.pairs})

    @property
    def unpaired_thermal_count(self) -> int:
        return len(self.thermal_batch.results) - len({p.thermal_frame_id for p in self.pairs})


def import_m3t_project(
    directory: str | Path,
    *,
    rgb_importer: M3TRGBImporter | None = None,
    thermal_importer: M3TImporter | None = None,
    minimum_pair_confidence: float = 0.70,
    candidate_percentile: float = 99.9,
    candidate_limit: int = 100,
) -> ProjectImportResult:
    """Import visible and thermal M3T imagery and pair matching frames."""
    root = Path(directory)
    rgb = (rgb_importer or M3TRGBImporter()).import_directory(root)
    thermal = import_m3t_directory(
        root, importer=thermal_importer,
        candidate_percentile=candidate_percentile, candidate_limit=candidate_limit,
    )
    thermal_frames = tuple(result.frame for result in thermal.results)
    pairs = pair_rgb_thermal_frames(rgb, thermal_frames, minimum_confidence=minimum_pair_confidence)
    return ProjectImportResult(rgb, thermal, pairs)
