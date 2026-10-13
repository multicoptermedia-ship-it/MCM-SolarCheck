"""Fictional customer-pilot example, explicitly not a real inspection."""
from __future__ import annotations

from mcm_solarcheck.services.pv_report_pilot_contract import PilotFinding, PilotReport


def fictional_pilot_report() -> PilotReport:
    return PilotReport(
        project="BEISPIEL-001 (fiktiv)",
        inspection_date="nicht erfasst",
        inspector="Musterprüfer (fiktiv)",
        plant="PV-Musteranlage – keine reale Anlage",
        conditions=None,
        limitations="Fiktives Layoutmuster ohne Messwerte, Originalbilder oder Inspektion.",
        site_address="Musterstraße 1, 12345 Musterstadt (fiktiv)",
        total_modules=120,
        conspicuous_modules=4,
        irradiance_w_m2=850,
        irradiance_source="manuelle Messung mit Messgerät (fiktiver Beispielwert)",
        findings=(PilotFinding("M-01 (fiktiv)", "Beispielhafte thermische Auffälligkeit; keine Diagnose.", reviewed=True),),
    )
