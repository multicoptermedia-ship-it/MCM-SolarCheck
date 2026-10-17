"""CLI regression for manual-review display without inspecting customer images."""
from zipfile import ZipFile

from mcm_solarcheck.services.flight_overlap_audit import FlightOverlapAudit, ImageTransition
from mcm_solarcheck.services import flight_zip_check


def test_overlap_cli_shows_review_without_approving_geometry(tmp_path, monkeypatch, capsys):
    path = tmp_path / "synthetic.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("DJI_20260725154422_0001_V.JPG", b"fake")
        archive.writestr("DJI_20260725154422_0001_T.JPG", b"fake")
    sample = FlightOverlapAudit(
        (ImageTransition("0015", "0016", 80, 46, .575, 3),),
        (ImageTransition("0017", "0018", 10, 6, .6, 4),),
        (),
    )
    monkeypatch.setattr(
        "mcm_solarcheck.services.flight_overlap_audit.audit_flight_overlap",
        lambda archive_path: sample,
    )
    assert flight_zip_check.main([str(path), "--audit-overlap"]) == 0
    output = capsys.readouterr().out
    assert "REVIEW RGB 0015->0016" in output
    assert "REVIEW Thermal 0017->0018" in output
    assert "Metric orthophoto approved: NO" in output
