"""Offline-only opt-in comparison of local anonymous DJI benchmark reports.

Example:
 python -m mcm_solarcheck.offline.benchmark_compare_cli \
     --reports run-01.json run-02.json run-03.json \
     --output comparison.json

All paths must be absolute. No network, images, customer projects, or
automatic output files are involved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from mcm_solarcheck.services.offline_benchmark_comparison import (
    compare_offline_benchmark_reports,
)
from mcm_solarcheck.services.offline_import_metrics import (
    save_anonymous_import_report,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare 3 to 30 successful local anonymized benchmark JSON reports. "
            "Identical image counts do not prove flight or hardware identity."
        ),
    )
    parser.add_argument(
        "--reports", type=Path, nargs="+", required=True,
        help="Three or more distinct absolute paths to schema-v2 reports",
    )
    parser.add_argument(
        "--output", type=Path,
        help="Optional absolute destination for anonymous JSON (never overwrite)",
    )
    args = parser.parse_args(argv)

    try:
        comparison = compare_offline_benchmark_reports(args.reports)
    except (ValueError, OSError, TypeError):
        # Never include source report names, private fields or local paths.
        print(
            "Vergleich nicht moeglich: mindestens drei gueltige, erfolgreiche, "
            "vergleichbare anonyme Benchmark-Berichte benoetigt.",
            file=sys.stderr,
        )
        return 2

    if args.output is not None:
        try:
            save_anonymous_import_report(comparison, args.output)
        except (ValueError, OSError):
            print(
                "Vergleichsbericht nicht gespeichert; Ausgabeziel pruefen.",
                file=sys.stderr,
            )
            return 3

    print(json.dumps(
        comparison.anonymous_report(), ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
