import pytest

from mcm_solarcheck.infrastructure.paramiko_handshake_driver import ParamikoHandshakeDriver
from mcm_solarcheck.infrastructure.sftp_host_key_pin import ssh_sha256_fingerprint
from mcm_solarcheck.infrastructure.sftp_storage_config import SFTPStorageConfig


class Socket:
    def __init__(self, events):
        self.events = events

    def close(self):
        self.events.append("socket_close")


class BrokenTransport:
    def __init__(self, sock, events):
        self.events = events

    def start_client(self, timeout):
        raise OSError("SSH negotiation failed")

    def close(self):
        self.events.append("transport_close")


def test_failed_ssh_negotiation_closes_transport_and_socket():
    events = []
    config = SFTPStorageConfig("example.test", 22, "user", "/private", ssh_sha256_fingerprint(b"key"))
    driver = ParamikoHandshakeDriver(
        config,
        socket_factory=lambda address, timeout: Socket(events),
        transport_factory=lambda sock: BrokenTransport(sock, events),
        credentials=lambda: {"password": "unused"},
    )
    with pytest.raises(OSError, match="negotiation"):
        driver.negotiate_without_authentication()
    assert events == ["transport_close", "socket_close"]


def test_invalid_authentication_payload_rejected():
    events = []
    class Key:
        def asbytes(self):
            return b"key"
    class Transport:
        def __init__(self, sock):
            pass
        def start_client(self, timeout):
            pass
        def get_remote_server_key(self):
            return Key()
        def close(self):
            pass
    config = SFTPStorageConfig("example.test", 22, "user", "/private", ssh_sha256_fingerprint(b"key"))
    driver = ParamikoHandshakeDriver(
        config,
        socket_factory=lambda address, timeout: Socket(events),
        transport_factory=Transport,
        credentials=lambda: {"unexpected": "value"},
    )
    driver.negotiate_without_authentication()
    with pytest.raises(ValueError, match="password"):
        driver.authenticate()
    driver.close()
