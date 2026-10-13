import pytest

from mcm_solarcheck.services.pv_pilot_sample_cli import main


def test_sample_pdf_requires_existing_parent(tmp_path):
    with pytest.raises(FileNotFoundError):
        main([str(tmp_path / "missing" / "sample.pdf")])


def test_sample_pdf_rejects_non_pdf_destination(tmp_path):
    with pytest.raises(ValueError):
        main([str(tmp_path / "sample.txt")])
