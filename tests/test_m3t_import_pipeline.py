from pathlib import Path

from mcm_solarcheck.domain.models import Pose, Position, RTKQuality
from mcm_solarcheck.importers.batch import import_m3t_directory
from mcm_solarcheck.importers.m3t import M3TImporter
from mcm_solarcheck.importers.m3t_xmp import M3TXmpMetadata
from mcm_solarcheck.thermal.m3t_radiometric import RadiometricRaster
from mcm_solarcheck.thermal.quality import ThermalQualityGrade


class FakeParser:
    def parse_bytes(self, data):
        values = tuple(19000 + (i % 1000) for i in range(640 * 512))
        return RadiometricRaster(640, 512, "little", values, 0)


def fake_xmp(data):
    return M3TXmpMetadata(
        timestamp_utc=None,
        position=Position(51.0, 6.5, 112.0),
        camera_pose=Pose(pitch_deg=-89.9),
        flight_pose=Pose(yaw_deg=93.3),
        rtk=RTKQuality(status="RTK", std_lat_m=0.01),
        camera_make="DJI",
        camera_model="M3T",
        image_source="InfraredCamera",
        raw={"GpsStatus": "RTK"},
    )


def test_frame_id_uses_dji_sequence_number():
    assert M3TImporter.frame_id(Path("DJI_20250825121339_0001_T.JPG")) == "T-0001"


def test_integrated_import(monkeypatch, tmp_path):
    import mcm_solarcheck.importers.m3t as module
    monkeypatch.setattr(module, "parse_m3t_xmp", fake_xmp)
    path = tmp_path / "DJI_20250825121339_0001_T.JPG"
    path.write_bytes(b"fake")
    result = M3TImporter(FakeParser()).import_file(path, candidate_limit=5)
    assert result.frame.camera_model == "M3T"
    assert result.frame.position.latitude == 51.0
    assert result.frame.temperature_matrix is None
    assert result.quality.grade == ThermalQualityGrade.PASS
    assert len(result.findings) == 5
    assert all(f.temperature_c is None for f in result.findings)


def test_batch_continues_after_failure(monkeypatch, tmp_path):
    import mcm_solarcheck.importers.m3t as module
    monkeypatch.setattr(module, "parse_m3t_xmp", fake_xmp)
    for number in (1, 2):
        (tmp_path / f"DJI_20250825_{number:04d}_T.JPG").write_bytes(b"fake")

    class SometimesFails(M3TImporter):
        def import_file(self, path, **kwargs):
            if "0002" in Path(path).name:
                raise ValueError("broken fixture")
            return super().import_file(path, **kwargs)

    batch = import_m3t_directory(tmp_path, importer=SometimesFails(FakeParser()), candidate_limit=2)
    assert batch.summary.total_files == 2
    assert batch.summary.imported == 1
    assert batch.summary.failed == 1
    assert batch.summary.finding_count == 2
    assert batch.failures[0].error_type == "ValueError"
