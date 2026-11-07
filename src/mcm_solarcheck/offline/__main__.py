"""Run the existing offline desktop product, never the online customer shell."""
from __future__ import annotations

import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile

from mcm_solarcheck.offline.entrypoint import main


def existing_database(value: str) -> Path:
    """Check only SQLite schema metadata, without creating/changing a file."""
    path = Path(value).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError("Vorhandene SolarCheck-Projektdatei auswaehlen.")
    path = path.resolve(strict=True)
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as database:
            if database.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'",
            ).fetchone() is None:
                raise ValueError()
            columns = {row[1] for row in database.execute('PRAGMA table_info(projects)')}
            if not {'project_id', 'name'} <= columns:
                raise ValueError()
    except (sqlite3.Error, ValueError):
        raise argparse.ArgumentTypeError("Die Datei ist keine vorhandene SolarCheck-Projektdatenbank.") from None
    return path


def backup_database(path: Path) -> Path:
    """Keep a consistent private snapshot, including committed WAL contents."""
    import os
    descriptor, filename = tempfile.mkstemp(
        prefix=path.stem + '.before-update-', suffix='.sqlite3', dir=path.parent,
    )
    os.close(descriptor)
    destination = Path(filename)
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def launch(argv=None) -> int:
    parser = argparse.ArgumentParser(description="MCM-SolarCheck Offline")
    parser.add_argument('--existing-database', type=existing_database,
                        help="Vorhandene Projektdatei lokal sichern und weiterverwenden")
    arguments, qt_arguments = parser.parse_known_args(argv)
    if arguments.existing_database is None:
        return main()
    # Complete backup BEFORE GUI initialization can migrate an older schema.
    backup_database(arguments.existing_database)
    return main(argv=[sys.argv[0], *qt_arguments], database_path=arguments.existing_database)


if __name__ == "__main__":
    raise SystemExit(launch())
