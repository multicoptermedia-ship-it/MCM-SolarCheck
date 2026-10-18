"""Flight inventory regression tests."""
import pytest
from mcm_solarcheck.services.flight_inventory import scan_flight


def test_all_captures_and_missing_modalities_are_visible(tmp_path):
    for index in range(1, 28):
        (tmp_path / f"DJI_20260725154421_{index:04d}_V.JPG").write_bytes(b"rgb")
        if index != 27:
            (tmp_path / f"DJI_20260725154421_{index:04d}_T.JPG").write_bytes(b"thermal")
    (tmp_path / "notes.txt").write_text("not an image")
    captures, ignored = scan_flight(tmp_path)
    assert len(captures) == 27
    assert sum(rgb is not None for _, rgb, _ in captures) == 27
    assert sum(thermal is not None for _, _, thermal in captures) == 26
    assert captures[-1][2] is None
    assert ignored == ("notes.txt",)


def test_duplicate_modality_rejected(tmp_path):
    (tmp_path / "DJI_20260725154421_0001_V.JPG").write_bytes(b"a")
    (tmp_path / "DJI_20260725154421_0001_V.PNG").write_bytes(b"b")
    with pytest.raises(ValueError, match="duplicate"):
        scan_flight(tmp_path)


def test_empty_folder_rejected(tmp_path):
    with pytest.raises(ValueError, match="no DJI"):
        scan_flight(tmp_path)
