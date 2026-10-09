"""Job status UI shows server state without fabricating findings."""
from shared_ui.server import UI_FILE


def test_job_status_ui_contract():
    html = UI_FILE.read_text(encoding="utf-8")
    assert 'id="job-status-button"' in html
    assert "'/api/compute-job?'" in html
    assert "credentials:'same-origin'" in html
    assert "currentJob={project_id:project,job_id:created.job_id}" in html
    assert "result.job_id!==currentJob.job_id" in html
    assert 'button disabled title="Berichts-API noch nicht angebunden"' in html
