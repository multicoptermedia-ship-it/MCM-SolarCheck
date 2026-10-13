from pathlib import Path
from mcm_solarcheck.services.pv_pilot_sample_cli import main
from mcm_solarcheck.services.pv_pilot_synthetic_evidence import synthetic_evidence


def test_sample_cli_creates_pdf(tmp_path):
    destination = tmp_path / "solarcheck-muster.pdf"
    assert main([str(destination)]) == destination
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 3000


def test_fixture_labels_are_explicit(tmp_path):
    items = synthetic_evidence(tmp_path)
    assert items[0].module == "M-01 (fiktiv)"
    assert "SYNTHETIC" in items[0].rgb_frame
    assert all(path.is_file() for path in (items[0].rgb_path, items[0].thermal_path))
