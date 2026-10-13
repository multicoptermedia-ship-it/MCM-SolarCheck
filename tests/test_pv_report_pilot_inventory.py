import pytest

from mcm_solarcheck.services.pv_report_pilot_contract import (
    PilotFinding, PilotReport, report_sections,
)
from mcm_solarcheck.services.pv_training_export_inventory import TrainingExportInventory


def test_report_marks_pilot_and_unknown_conditions():
    report = PilotReport(
        "Project", "2026-10-13", "Expert", "PV system", None, "No irradiance record",
        (PilotFinding("M-1", "Thermal anomaly", reviewed=True),),
    )
    sections = dict(report_sections(report))
    assert "kein Normkonformitätsnachweis" in sections["Grundlage"]
    assert sections["Prüfbedingungen"] == "nicht erfasst"
    assert "M-1" in sections["Feststellungen"]


def test_unreviewed_findings_are_rejected():
    with pytest.raises(PermissionError):
        PilotReport("P", "2026", "E", "PV", None, "Limitations",
                    (PilotFinding("M-1", "Hotspot"),))


def test_inventory_withdrawal_detects_changed_files(tmp_path):
    root = tmp_path / "exports"
    root.mkdir()
    inventory = TrainingExportInventory(tmp_path / "inventory.db", root)
    a = "a" * 32 + ".png"
    b = "b" * 32 + ".png"
    (root / a).write_bytes(b"first")
    (root / b).write_bytes(b"second")
    inventory.register("project", a)
    inventory.register("project", b)
    (root / b).write_bytes(b"modified")
    assert inventory.withdraw("project") == {
        "deleted_or_missing": 1, "changed_requires_review": 1,
    }
    assert not (root / a).exists()
    assert (root / b).exists()
