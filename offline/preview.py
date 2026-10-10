"""Offline shared-UI preview, backed by the existing local project database."""
import argparse
from pathlib import Path
from shared_ui.server import serve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", type=Path, default=Path.home() / "MCM-SolarCheck" / "solarcheck.sqlite3")
    args = parser.parse_args()
    serve("offline", args.port, database_path=args.database)


if __name__ == "__main__":
    main()
