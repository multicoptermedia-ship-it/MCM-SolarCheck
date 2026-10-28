"""Protect the SINGLE current SolarCheck development handoff entrypoint.

The change does not touch photogrammetry or private project data.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_handoff_is_visible_from_repository_entrypoints():
    checkpoint = ROOT / "docs" / "AKTUELLER_ENTWICKLUNGSSTAND.md"
    assert checkpoint.is_file()
    content = checkpoint.read_text(encoding="utf-8")
    # Current handoff must stay short enough to actually be read on chat restart.
    assert 1000 <= len(content) <= 8500
    for phrase in (
        "Verbindlicher Erstlesepunkt",
        "DEV-RGB-ORTHO-ENGINE-001",
        "Mehrbild-Photogrammetrie",
        "ODM / WebODM / ODX NICHT",
        "PR #7", "PR #8", "PR #9",
        "kein Merge", "keine",
    ):
        assert phrase.lower() in content.lower(), phrase
    for doc in (
        "README.md", "docs/PROJECT_START_HERE.md",
        "docs/DEVELOPMENT_AGREEMENT.md", "docs/CHAT_HANDOFF.md",
        "docs/DEVELOPMENT_STEP_REGISTER.md",
        "docs/PV_ORTHOMOSAIC_FIRST_ROADMAP.md",
    ):
        source = (ROOT / doc).read_text(encoding="utf-8")
        assert "AKTUELLER_ENTWICKLUNGSSTAND.md" in source, doc


def test_historical_readme_cannot_assign_odm_as_active_backend():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "kein" in text.lower() and "ODM/WebODM/ODX" in text
    assert "- OpenDroneMap/WebODM bzw. kompatible" not in text
    assert "## Historischer Planungsabschnitt" in text
