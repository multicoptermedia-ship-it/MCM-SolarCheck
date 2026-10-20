"""Opt-in thermal raster eviction: legacy parity, bounded retention, no Celsius claims."""
from __future__ import annotations

import gc
from pathlib import Path
from types import SimpleNamespace
import weakref

import pytest

from mcm_solarcheck.domain.models import Finding, ThermalFrame
from mcm_solarcheck.importers.batch import import_m3t_directory
from mcm_solarcheck.importers.m3t import M3TImportResult
from mcm_solarcheck.importers.project import import_m3t_project
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.m3t_radiometric import RadiometricRaster
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult


class SyntheticThermalImporter:
    """Produces realistic-size raster containers without decoding any real DJI image."""

    def __init__(self, *, fail_indices=()):
        self.raster_refs = []
        self.fail_indices = frozenset(fail_indices)

    def import_file(self, path, *, candidate_percentile=99.9, candidate_limit=100):
        index = int(Path(path).stem.split("_")[-2])
        if index in self.fail_indices:
            raise ValueError(f"synthetic broken thermal frame {index}")
        # Simulate the retained 640x512 pixel tuple without large JPEG fixtures.
        raster = RadiometricRaster(
            640, 512, "little", (1000 + index,) * (640 * 512), index,
        )
        self.raster_refs.append(weakref.ref(raster))
        frame = ThermalFrame(
            frame_id=f"T-{index:04d}",
            source_file=Path(path),
            thermal_width=640,
            thermal_height=512,
            thermal_source="DJI M3T APP3 raw",
        )
        quality = ThermalQualityResult(
            ThermalQualityGrade.PASS, (),
            RawThermalStatistics(
                1000 + index, 1000 + index, 1000.0 + index,
                1000.0 + index, 1000.0 + index, 1000.0 + index, 0,
            ),
        )
        findings = (Finding(
            f"F-{index:04d}", frame.frame_id, 1, 2,
            raw_value=1000 + index,
        ),)
        return M3TImportResult(
            frame=frame, raster=raster, quality=quality,
            candidates=(), findings=findings,
            xmp=SimpleNamespace(raw={"ImageSource": "InfraredCamera"}),
        )


def fake_thermal_directory(tmp_path, count):
    for index in range(count):
        (tmp_path / f"DJI_20261020_{index:04d}_T.JPG").touch()


def test_compact_batch_releases_each_large_raster_but_keeps_analysis(tmp_path):
    fake_thermal_directory(tmp_path, 72)
    importer = SyntheticThermalImporter()
    compact = import_m3t_directory(
        tmp_path, importer=importer, retain_rasters=False,
        candidate_limit=5,
    )
    assert compact.summary.total_files == 72
    assert compact.summary.imported == 72
    assert compact.summary.failed == 0
    assert compact.summary.finding_count == 72
    assert all(item.raster is None for item in compact.results)
    assert compact.results[0].frame.frame_id == "T-0000"
    assert compact.results[-1].frame.frame_id == "T-0071"
    assert all(len(item.findings) == 1 for item in compact.results)
    assert all(item.findings[0].temperature_c is None for item in compact.results)
    assert compact.results[20].quality.grade == ThermalQualityGrade.PASS
    gc.collect()
    assert len(importer.raster_refs) == 72
    assert all(ref() is None for ref in importer.raster_refs), (
        "compact batch retained full thermal raw rasters in memory"
    )


def test_default_batch_keeps_original_rasters_for_legacy_consumers(tmp_path):
    fake_thermal_directory(tmp_path, 2)
    importer = SyntheticThermalImporter()
    ordinary = import_m3t_directory(tmp_path, importer=importer)
    assert ordinary.summary.imported == 2
    assert all(item.raster is not None for item in ordinary.results)
    assert ordinary.results[0].raster.pixel_count == 640 * 512
    gc.collect()
    assert all(ref() is not None for ref in importer.raster_refs)


def test_failures_and_summary_are_unchanged_by_memory_option(tmp_path):
    fake_thermal_directory(tmp_path, 4)
    worker = SyntheticThermalImporter(fail_indices=(1, 3))
    summary = import_m3t_directory(
        tmp_path, importer=worker, retain_rasters=False,
    )
    assert summary.summary.total_files == 4
    assert summary.summary.imported == 2
    assert summary.summary.failed == 2
    assert summary.summary.finding_count == 2
    assert {failure.error_type for failure in summary.failures} == {"ValueError"}
    assert all(item.raster is None for item in summary.results)


@pytest.mark.parametrize("invalid", [None, 0, 1, "false", (), []])
def test_compaction_requires_an_explicit_boolean(tmp_path, invalid):
    with pytest.raises(ValueError, match="retain_rasters"):
        import_m3t_directory(tmp_path, retain_rasters=invalid)


def test_project_orchestrator_forwards_opt_in_without_changing_default(
    tmp_path, monkeypatch,
):
    import mcm_solarcheck.importers.project as module

    observed = []

    class RGB:
        def import_directory(self, directory, *, heartbeat=None):
            return ()

    def fake_thermal(directory, **kwargs):
        observed.append(kwargs["retain_rasters"])
        return SimpleNamespace(results=(), failures=())

    monkeypatch.setattr(module, "import_m3t_directory", fake_thermal)
    monkeypatch.setattr(
        module, "pair_rgb_thermal_frames",
        lambda rgb, thermal, *, minimum_confidence, heartbeat: (),
    )

    normal = import_m3t_project(tmp_path, rgb_importer=RGB())
    compact = import_m3t_project(
        tmp_path, rgb_importer=RGB(), retain_rasters=False,
    )
    assert observed == [True, False]
    assert normal.thermal_batch.results == ()
    assert compact.thermal_batch.results == ()
