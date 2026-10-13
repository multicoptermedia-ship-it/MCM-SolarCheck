"""CLI entry point for a completely fictional local PDF report."""
from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.pv_pilot_synthetic_evidence import synthetic_evidence
from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
from mcm_solarcheck.services.pv_pilot_synthetic_flight import fictional_flight_overview


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description="Create fictional SolarCheck layout sample")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    with TemporaryDirectory(prefix="solarcheck-fictional-") as folder:
        result = export_pilot_pdf(
            fictional_pilot_report(), args.destination,
            evidence=synthetic_evidence(Path(folder)),
            flight_overview=fictional_flight_overview(Path(folder)),
        )
    return result


if __name__ == "__main__":
    print(main())
