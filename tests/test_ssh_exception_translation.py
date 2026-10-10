import errno
from types import SimpleNamespace

import pytest

from mcm_solarcheck.infrastructure.sftp_connection_errors import (
    SFTPNetworkError, SFTPPermissionError, SFTPTimeoutError,
)
from mcm_solarcheck.infrastructure.ssh_exception_translation import translate_ssh_exception
from mcm_solarcheck.infrastructure.strict_sftp_directory_inspection import StrictReadOnlySFTPSession


def test_known_errors_are_translated_without_secret_messages():
    assert isinstance(translate_ssh_exception(TimeoutError("password=secret")), SFTPTimeoutError)
    assert isinstance(translate_ssh_exception(ConnectionResetError(errno.ECONNRESET, "secret")), SFTPNetworkError)
    assert isinstance(translate_ssh_exception(PermissionError(errno.EACCES, "secret")), SFTPPermissionError)


def test_unknown_errors_preserved_for_caller():
    error = ValueError("unclassified")
    assert translate_ssh_exception(error) is error


@pytest.mark.parametrize("error,expected", [
    (FileNotFoundError(errno.ENOENT, "missing"), False),
    (PermissionError(errno.EACCES, "denied"), SFTPPermissionError),
    (ConnectionResetError(errno.ECONNRESET, "reset"), SFTPNetworkError),
])
def test_strict_directory_inspection(error, expected):
    class Client:
        def stat(self, path):
            raise error
        def close(self):
            pass

    session = StrictReadOnlySFTPSession(Client())
    if expected is False:
        assert session.directory_exists("/private") is False
    else:
        with pytest.raises(expected):
            session.directory_exists("/private")


def test_directory_stat_success():
    class Client:
        def stat(self, path):
            return SimpleNamespace(st_mode=0o040755)
        def close(self):
            pass
    assert StrictReadOnlySFTPSession(Client()).directory_exists("/private")
