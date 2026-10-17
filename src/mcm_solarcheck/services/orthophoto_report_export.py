"""Create a local PDF report with an RGB orthophoto illustration."""
from pathlib import Path
from tempfile import TemporaryDirectory
from mcm_solarcheck.services.orthophoto_report_overview import create_rgb_orthophoto_report_preview
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf


def export_pilot_pdf_with_rgb_orthophoto(report, rgb_geotiff, destination, *, evidence=()):
    target = Path(destination)
    if target.suffix.lower() != '.pdf' or not target.parent.is_dir():
        raise ValueError('existing output directory and PDF destination required')
    if target.exists():
        raise FileExistsError('report destination already exists')
    with TemporaryDirectory(prefix='.mcm-report-preview-', dir=target.parent) as directory:
        overview = create_rgb_orthophoto_report_preview(rgb_geotiff, Path(directory) / 'rgb.png')
        return export_pilot_pdf(report, target, evidence=evidence, flight_overview=overview)
