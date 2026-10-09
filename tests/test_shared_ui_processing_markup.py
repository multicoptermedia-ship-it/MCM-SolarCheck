"""Processing controls use existing jobs and show only backend results."""
from shared_ui.server import UI_FILE


def test_processing_ui_requires_existing_job():
    html = UI_FILE.read_text(encoding="utf-8")
    assert 'id="processing-job"' in html
    assert "Bitte Projekt und vorhandene Job-ID angeben." in html
    assert "fetch(url,{method:'POST'" in html
    assert "'/api/project-process?'" in html
    assert "result.state!=='completed'" in html
    assert "Number(result.imported_thermal_frames)" in html
