"""Opt-in command-line benchmark for real local DJI imports on Windows.

Invoke in a new interpreter to make process-lifetime peak RSS comparable:
    python -m mcm_solarcheck.offline.benchmark_cli --source ABSOLUTE_DIRECTORY

No network communication, customer database updates, or automatic file export.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from mcm_solarcheck.services.offline_import_benchmark import (
    run_offline_import_benchmark,
)
from mcm_solarcheck.services.offline_import_metrics import (
    save_anonymous_import_report,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one isolated offline DJI import against a temporary SQLite DB. "
            "Use a new Python process for each run; RSS covers process lifetime."
        )
    )
    parser.add_argument(
        "--source", required=True, type=Path,
        help="Absolute path to an existing local DJI image directory",
    )
    parser.add_argument(
        "--workspace", type=Path,
        help="Optional existing absolute local directory for temporary SQLite",
    )
    parser.add_argument(
        "--output", type=Path,
        help="Optional absolute JSON destination; never overwritten",
    )
    args = parser.parse_args(argv)

    try:
        result = run_offline_import_benchmark(
            args.source, workspace=args.workspace,
        )
    except Exception:
        # Import exceptions may contain customer names or image paths.
        print(
            "Benchmark konnte nicht gestartet werden; lokale Verzeichnisse, "
            "Zugriffsrechte und Installation pruefen.",
            file=sys.stderr,
        )
        return 2

    if args.output is not None:
        try:
            # Both reports expose an allowlisted anonymous_report() object.
            # Reuse the existing exclusive, symlink-guarded JSON writer.
            save_anonymous_import_report(result, args.output)
        except (OSError, ValueError):
            print(
                "Anonymer Bericht nicht gespeichert; Ziel und "
                "bestehende Datei pruefen.",
                file=sys.stderr,
            )
            return 3

    # No source paths, project IDs, raw errors or file contents on stdout.
    print(json.dumps(result.anonymous_report(), ensure_ascii=False, indent=2))
    return {"succeeded": 0, "failed": 1, "cancelled": 130}[
        result.measurement.outcome
    ]


if __name__ == "__main__":
    raise SystemExit(main())
