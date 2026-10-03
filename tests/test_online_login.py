from __future__ import annotations

import pytest

from mcm_solarcheck.services.online_login import OnlineLoginService


class Credentials:
    def __init__(self, valid=True) -> None:
        self.valid = valid
        self.calls = []

    def verify_password(self, user_id, password):
        self.calls.append((user_id, password))
        return self.valid


class Identities:
    def __init__(self, verified=True) -> None:
        self.verified = verified
        self.calls = []

    def require_verified_identity(self, user_id):
        self.calls.append(user_id)
        if not self.verified:
            raise PermissionError("online identity is not verified")
        return user_id


def test_login_returns_verified_identity_after_valid_credentials() -> None:
    credentials = Credentials()
    identities = Identities()
    login = OnlineLoginService(credentials, identities)

    assert login.login("user-1", "correct horse battery staple") == "user-1"
    assert credentials.calls == [("user-1", "correct horse battery staple")]
    assert identities.calls == ["user-1"]


def test_login_rejects_bad_credentials_before_identity_admission() -> None:
    credentials = Credentials(valid=False)
    identities = Identities()
    login = OnlineLoginService(credentials, identities)

    with pytest.raises(PermissionError, match="invalid online login"):
        login.login("user-1", "wrong password value")
    assert identities.calls == []


def test_login_masks_unverified_identity_as_invalid_login() -> None:
    login = OnlineLoginService(Credentials(), Identities(verified=False))

    with pytest.raises(PermissionError, match="invalid online login"):
        login.login("user-1", "correct horse battery staple")


def test_login_masks_invalid_credential_input() -> None:
    class RejectingCredentials:
        def verify_password(self, user_id, password):
            raise ValueError("password must contain at least 12 characters")

    login = OnlineLoginService(RejectingCredentials(), Identities())

    with pytest.raises(PermissionError, match="invalid online login"):
        login.login("user-1", "short")
