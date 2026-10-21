"""Explicit, interactive CLI bootstrap for a separate offline audit administrator.

Usage: python -m mcm_solarcheck.offline.admin_setup
No password command-line arguments, default accounts or automatic provisioning.
"""
from __future__ import annotations

import argparse
from getpass import getpass

from mcm_solarcheck.offline.entrypoint import default_database_path
from mcm_solarcheck.services.offline_admin_credentials import (
    create_offline_admin_credentials, default_admin_credential_path,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Set up offline report-audit administrator")
    parser.add_argument("--database", default=str(default_database_path()),
                        help="Local inspection database path (only its directory is used)")
    values = parser.parse_args(argv)
    credentials = default_admin_credential_path(values.database)
    actor = input("Neue Administrator-ID: ").strip()
    password = getpass("Neues Passwort (mind. 12 Zeichen): ")
    confirmation = getpass("Passwort wiederholen: ")
    if password != confirmation:
        raise SystemExit("Passwörter stimmen nicht überein; keine Änderung.")
    create_offline_admin_credentials(credentials, actor, password)
    print("Lokale Administratoranmeldung angelegt. Kein Passwort ausgegeben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
