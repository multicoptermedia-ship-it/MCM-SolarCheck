"""Single export boundary for all Phase 9 report formats."""
from __future__ import annotations
from pathlib import Path
from .docx_renderer import render_docx
from .odt_renderer import render_odt
from .pdf_renderer import render_pdf
from .report_model import InspectionReport

_FORMATS={"docx":render_docx,"odt":render_odt,"pdf":render_pdf}


def export_report(report: InspectionReport, destination: str | Path, *, format: str | None=None, banner_path: str | Path | None=None) -> Path:
    destination=Path(destination)
    selected=(format or destination.suffix.lstrip(".")).lower()
    if selected not in _FORMATS: raise ValueError(f"unsupported report format: {selected or '<missing>'}")
    if destination.suffix.lower()!=f".{selected}": raise ValueError("destination extension must match report format")
    renderer=_FORMATS[selected]
    return renderer(report,destination,banner_path=banner_path)
