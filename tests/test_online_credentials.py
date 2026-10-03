from __future__ import annotations

import pytest

from mcm_solarcheck.services.online_credentials import PasswordCredentialService


class Credentials:
    def __init__(self) -> None:
        self.values = {}

    def save(self, credential) -> None:
        self.values[credential.user_id] = credential

    def get(self, user_id):
        if user_id not in self.values:
            raise KeyError(user_id)
        return self.values[user_id]


def test_password_service_persists_only_salted_derived_credential() -> None:
    store = Credentials()
    service = PasswordCredentialService(store)

    service.set_password("user-1", "correct horse battery staple")

    credential = store.values["user-1"]
    assert credential.digest_hex != "correct horse battery staple"
    assert "correct horse battery staple" not in repr(credential)
    assert credential.salt_hex
    assert service.verify_password("user-1", "correct horse battery staple")


def test_password_service_rejects_wrong_password() -> None:
    store = Credentials()
    service = PasswordCredentialService(store)
    service.set_password("user-1", "correct horse battery staple")

    assert not service.verify_password("user-1", "incorrect password value")


def test_password_service_rejects_unknown_identity_without_leaking_store_error() -> None:
    service = PasswordCredentialService(Credentials())

    assert not service.verify_password("missing", "correct horse battery staple")


def test_password_service_rejects_short_password() -> None:
    service = PasswordCredentialService(Credentials())

    with pytest.raises(ValueError, match="at least 12"):
        service.set_password("user-1", "too-short")
