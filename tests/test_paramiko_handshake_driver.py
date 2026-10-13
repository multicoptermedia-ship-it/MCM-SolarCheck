import pytest

from mcm_solarcheck.infrastructure.paramiko_handshake_driver import ParamikoHandshakeDriver
from mcm_solarcheck.infrastructure.paramiko_probe_composition import build_paramiko_read_only_probe
from mcm_solarcheck.infrastructure.sftp_host_key_pin import ssh_sha256_fingerprint
from mcm_solarcheck.infrastructure.sftp_storage_config import SFTPStorageConfig


class FakeSocket:
    def __init__(self, events):
        self.events = events

    def close(self):
        self.events.append("socket_close")


class FakeKey:
    def __init__(self, blob):
        self.blob = blob

    def asbytes(self):
        return self.blob


class FakeTransport:
    def __init__(self, sock, events, blob):
        self.events = events
        self.blob = blob
        self.authenticated = False

    def start_client(self, timeout):
        self.events.append("handshake")

    def get_remote_server_key(self):
        self.events.append("server_key")
        return FakeKey(self.blob)

    def auth_password(self, username, password):
        self.events.append("authenticate")
        self.authenticated = True

    def is_authenticated(self):
        return self.authenticated

    def close(self):
        self.events.append("transport_close")


def config(blob):
    return SFTPStorageConfig("example.test", 22, "user", "/private", ssh_sha256_fingerprint(blob))


def test_paramiko_driver_does_not_request_credentials_before_verified_key():
    events = []
    probe = build_paramiko_read_only_probe(
        credentials_provider=lambda: events.append("credentials") or {"password": "fake"},
        socket_factory=lambda address, timeout: FakeSocket(events),
        transport_factory=lambda sock: FakeTransport(sock, events, b"wrong"),
    )
    with pytest.raises(ValueError, match="mismatch"):
        probe.inspect(config(b"right"))
    assert "credentials" not in events
    assert "authenticate" not in events
    assert "handshake" in events
    assert "transport_close" in events
    assert "socket_close" in events


def test_driver_requires_credentials_provider_before_authentication():
    events = []
    driver = ParamikoHandshakeDriver(
        config(b"right"),
        socket_factory=lambda address, timeout: FakeSocket(events),
        transport_factory=lambda sock: FakeTransport(sock, events, b"right"),
    )
    driver.negotiate_without_authentication()
    with pytest.raises(PermissionError):
        driver.authenticate()
    driver.close()
    assert "authenticate" not in events
