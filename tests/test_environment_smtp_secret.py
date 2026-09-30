from __future__ import annotations

import pytest

from mcm_solarcheck.infrastructure.environment_smtp_secret import EnvironmentSMTPSecretStore


def test_environment_secret_reports_only_presence() -> None:
    environment: dict[str, str] = {}
    store = EnvironmentSMTPSecretStore(environment=environment)

    assert store.is_set() is False

    store.replace("smtp-secret")

    assert store.is_set() is True
    assert environment["SOLARCHECK_SMTP_PASSWORD"] == "smtp-secret"


def test_environment_secret_resolves_only_for_internal_delivery() -> None:
    environment = {"SOLARCHECK_SMTP_PASSWORD": "smtp-secret"}
    store = EnvironmentSMTPSecretStore(environment=environment)

    assert store.resolve_for_delivery() == "smtp-secret"


def test_environment_secret_requires_configuration() -> None:
    store = EnvironmentSMTPSecretStore(environment={})

    with pytest.raises(RuntimeError, match="not configured"):
        store.resolve_for_delivery()


def test_environment_secret_rejects_empty_replacement() -> None:
    store = EnvironmentSMTPSecretStore(environment={})

    with pytest.raises(ValueError, match="password"):
        store.replace("")
