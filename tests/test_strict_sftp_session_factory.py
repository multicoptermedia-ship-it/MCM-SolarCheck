import errno
from types import SimpleNamespace

import pytest

from mcm_solarcheck.infrastructure.sftp_connection_errors import SFTPPermissionError, SFTPNetworkError
from mcm_solarcheck.infrastructure.strict_sftp_session_factory import open_strict_sftp_session


class Transport:
    def __init__(self, authenticated=True):
        self.authenticated = authenticated

    def is_authenticated(self):
        return self.authenticated


class Client:
    def __init__(self, error=None):
        self.error = error
        self.closed = False

    def stat(self, path):
        if self.error:
            raise self.error
        return SimpleNamespace(st_mode=0o040755)

    def close(self):
        self.closed = True


def test_factory_requires_authentication_before_creating_client():
    invoked = []
    with pytest.raises(PermissionError):
        open_strict_sftp_session(
            Transport(False), sftp_client_factory=lambda _: invoked.append(True)
        )
    assert not invoked


def test_directory_permission_error_not_reported_as_missing():
    client = Client(PermissionError(errno.EACCES, "secret"))
    session = open_strict_sftp_session(Transport(), sftp_client_factory=lambda _: client)
    with pytest.raises(SFTPPermissionError):
        session.directory_exists("/private")
    session.close()
    assert client.closed


def test_network_error_during_sftp_open_is_classified():
    with pytest.raises(SFTPNetworkError):
        open_strict_sftp_session(
            Transport(),
            sftp_client_factory=lambda _: (_ for _ in ()).throw(
                ConnectionResetError(errno.ECONNRESET, "secret")
            ),
        )


def test_missing_directory_only_returns_false_for_enoent():
    session = open_strict_sftp_session(
        Transport(),
        sftp_client_factory=lambda _: Client(FileNotFoundError(errno.ENOENT, "missing")),
    )
    assert session.directory_exists("/missing") is False
