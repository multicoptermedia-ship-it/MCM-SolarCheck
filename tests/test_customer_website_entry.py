from pathlib import Path


WEB = Path(__file__).parents[1] / "web" / "customer-site"


def test_customer_site_exposes_online_entry_without_offline_public_link() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "data-solarcheck-online-entry" in html
    assert "online-entry-config.js" in html
    assert "SolarCheck Offline" not in html


def test_online_entry_is_fail_closed_without_deployment_url() -> None:
    script = (WEB / "online-entry-config.js").read_text(encoding="utf-8")
    assert 'entry.setAttribute("aria-disabled", "true")' in script
    assert 'target.protocol === "https:" || target.protocol === "http:"' in script
