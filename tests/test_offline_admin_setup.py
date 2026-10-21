"""Offline audit bootstrap CLI requires two secret prompts without echo."""
import pytest

from mcm_solarcheck.offline import admin_setup
from mcm_solarcheck.services.offline_admin_credentials import (
    default_admin_credential_path, verify_offline_admin_credentials,
)


def test_cli_creates_credential_only_after_matching_prompt(monkeypatch, tmp_path):
    database = tmp_path / "local.sqlite3"
    path = default_admin_credential_path(database)
    monkeypatch.setattr("builtins.input", lambda *a: "Audit-Leitung")
    passwords = iter(["very long secure example pass", "mismatch"])
    monkeypatch.setattr(admin_setup, "getpass", lambda *a: next(passwords))
    with pytest.raises(SystemExit, match="stimmen nicht"):
        admin_setup.main(["--database", str(database)])
    assert not path.exists()
    passwords = iter(["very long secure example pass"] * 2)
    monkeypatch.setattr(admin_setup, "getpass", lambda *a: next(passwords))
    assert admin_setup.main(["--database", str(database)]) == 0
    assert verify_offline_admin_credentials(
        path, "Audit-Leitung", "very long secure example pass",
    )
    passwords = iter(["very long secure example pass"] * 2)
    monkeypatch.setattr(admin_setup, "getpass", lambda *a: next(passwords))
    with pytest.raises(FileExistsError):
        admin_setup.main(["--database", str(database)])
