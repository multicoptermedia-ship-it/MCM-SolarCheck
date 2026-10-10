"""Processing UI creates its own server-side job and respects admission."""
from shared_ui.server import UI_FILE


def test_processing_ui_creates_job_without_manual_id():
    html = UI_FILE.read_text(encoding="utf-8")
    assert 'id="processing-button"' in html
    assert "fetch('/api/compute-jobs'" in html
    assert "new URLSearchParams({project_id:project})" in html
    assert "created.status==='queued'" in html
    assert "created.status!=='running'" in html
    assert "'/api/project-process?'" in html
    assert "result.state!=='completed'" in html
