"""PDF text extraction smoke test for fictional customer layout."""
from pathlib import Path

import pytest

from mcm_solarcheck.services.pv_pilot_sample_cli import main


def test_sample_pdf_text_is_extractable(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    destination = tmp_path / "muster.pdf"
    main([str(destination)])
    reader = pypdf.PdfReader(str(destination))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "BEISPIEL-001" in text
    assert "M-01" in text
    assert "SYNTHETIC-RGB" in text
    assert "SYNTHETIC-THERMAL" in text
    assert "nicht erfasst" in text
