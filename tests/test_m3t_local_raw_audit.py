"""Privacy-safe tests for radiometric audit of selected ZIP pairs."""
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from mcm_solarcheck.services.m3t_local_raw_audit import audit_m3t_raw_archive


def make_zip(path, modality, count):
    with ZipFile(path, "w") as archive:
        for i in range(1, count + 1):
            archive.writestr(f"DJI_20250825121339_{i:04d}_{modality}.JPG", str(i).encode())


def test_audit_only_29_selected_frames(tmp_path, monkeypatch):
    t, v = tmp_path / "thermal.zip", tmp_path / "rgb.zip"
    make_zip(t, "T", 36)
    make_zip(v, "V", 29)
    seen = []
    def parse(self, data):
        seen.append(int(data))
        return SimpleNamespace(width=640, height=512, pixel_count=640 * 512)
    monkeypatch.setattr(
        "mcm_solarcheck.services.m3t_local_raw_audit.M3TRadiometricParser.parse_bytes", parse
    )
    result = audit_m3t_raw_archive(t, v)
    assert result.selected_pairs == result.radiometric_pass == 29
    assert result.radiometric_fail == 0
    assert result.sample_count == 29 * 640 * 512
    assert seen == list(range(1, 30))


def test_failed_frame_is_reported_without_data(tmp_path, monkeypatch):
    t, v = tmp_path / "thermal.zip", tmp_path / "rgb.zip"
    make_zip(t, "T", 2)
    make_zip(v, "V", 2)
    def parse(self, data):
        if data == b"2":
            raise ValueError("bad raw stream")
        return SimpleNamespace(width=640, height=512, pixel_count=640 * 512)
    monkeypatch.setattr(
        "mcm_solarcheck.services.m3t_local_raw_audit.M3TRadiometricParser.parse_bytes", parse
    )
    result = audit_m3t_raw_archive(t, v, count=2)
    assert result.radiometric_pass == 1
    assert result.radiometric_fail == 1
    assert result.failed_sequences == ("0002",)


def test_missing_rgb_blocks_audit(tmp_path):
    t, v = tmp_path / "thermal.zip", tmp_path / "rgb.zip"
    make_zip(t, "T", 2)
    make_zip(v, "V", 1)
    with pytest.raises(ValueError, match="lacks"):
        audit_m3t_raw_archive(t, v, count=2)
