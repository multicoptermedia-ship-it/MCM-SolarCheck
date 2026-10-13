import socket

import pytest

from mcm_solarcheck.infrastructure.paramiko_handshake_driver import ParamikoHandshakeDriver
from mcm_solarcheck.infrastructure.sftp_connection_errors import SFTPTimeoutError
from mcm_solarcheck.infrastructure.sftp_failure_classifier import classify_sftp_failure
from mcm_solarcheck.infrastructure.sftp_host_key_pin import ssh_sha256_fingerprint
from mcm_solarcheck.infrastructure.sftp_storage_config import SFTPStorageConfig


def config():
    return SFTPStorageConfig("example.test", 22, "user", "/private", ssh_sha256_fingerprint(b"key"))


@pytest.mark.parametrize("timeout", [0, -1, 121, True, "15"])
def test_invalid_timeouts_rejected(timeout):
    with pytest.raises(ValueError):
        ParamikoHandshakeDriver(config(), timeout=timeout)


def test_socket_timeout_is_classified_and_socket_cleaned():
    class FakeSocket:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    sock = FakeSocket()

    def broken_transport(_):
        raise socket.timeout("timed out")

    driver = ParamikoHandshakeDriver(
        config(), socket_factory=lambda address, timeout: sock,
        transport_factory=broken_transport,
    )
    with pytest.raises(SFTPTimeoutError) as exc:
        driver.negotiate_without_authentication()
    assert classify_sftp_failure(exc.value) == "timeout"
    driver.close()
    assert sock.closed == 1


def test_classifier_does_not_expose_exception_message():
    assert classify_sftp_failure(OSError("password=secret")) == "unknown"
    assert classify_sftp_failure(ConnectionRefusedError("secret")) == "network"
    assert classify_sftp_failure(PermissionError("secret")) == "permission"
