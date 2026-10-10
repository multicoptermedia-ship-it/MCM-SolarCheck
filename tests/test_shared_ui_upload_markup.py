"""Shared UI upload controls call the existing online upload endpoint."""
from shared_ui.server import UI_FILE


def test_online_upload_uses_existing_server_endpoint():
    html = UI_FILE.read_text(encoding="utf-8")
    assert 'id="upload-project"' in html
    assert 'id="upload-file"' in html
    assert "fetch('/project-upload'" in html
    assert "'X-SolarCheck-Project-Id':project" in html
    assert "'X-SolarCheck-Filename':file.name" in html
    assert "credentials:'same-origin'" in html
    assert "data.mode==='online'&&j.projects.length" in html
