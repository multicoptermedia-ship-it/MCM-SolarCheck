"""UI retains safeguards while server remains authoritative."""
from shared_ui.server import UI_FILE


def test_upload_client_limits_and_no_fake_analysis():
    html = UI_FILE.read_text(encoding="utf-8")
    assert "file.size===0||file.size>250*1024*1024" in html
    assert "Upload vom Server bestätigt. Analyse ist noch nicht gestartet." in html
    assert "button.disabled=true" in html
    assert "button.disabled=false" in html
    assert 'id="processing-job"' in html
    assert "Bitte Projekt und vorhandene Job-ID angeben." in html
    assert "result.state!=='completed'" in html
    assert 'button disabled title="Berichts-API noch nicht angebunden"' in html
