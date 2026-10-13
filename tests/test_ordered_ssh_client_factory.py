import pytest

from mcm_solarcheck.infrastructure.sftp_host_key_pin import ssh_sha256_fingerprint
from mcm_solarcheck.infrastructure.sftp_storage_config import SFTPStorageConfig
from mcm_solarcheck.infrastructure.ordered_sftp_probe_composition import build_ordered_verified_sftp_probe


class Driver:
    def __init__(self, key):
        self.key = key
        self.calls = []

    def negotiate_without_authentication(self):
        self.calls.append("negotiate")

    def negotiated_host_key_blob(self):
        self.calls.append("key")
        return self.key

    def authenticate(self):
        self.calls.append("authenticate")

    def open_read_only_sftp(self):
        self.calls.append("sftp")
        return self

    def directory_exists(self, path):
        self.calls.append("read")
        return path == "/private"

    def close(self):
        self.calls.append("close")


def config(key):
    return SFTPStorageConfig("example.test", 22, "user", "/private", ssh_sha256_fingerprint(key))


def test_ordered_probe_authenticates_only_after_host_key_match():
    driver = Driver(b"right")
    result = build_ordered_verified_sftp_probe(lambda _: driver).inspect(config(b"right"))
    assert result["root_exists"] is True
    assert driver.calls.index("authenticate") > driver.calls.index("key")
    assert driver.calls.index("sftp") > driver.calls.index("authenticate")
    assert driver.calls[-1] == "close"


def test_wrong_key_blocks_authentication_and_sftp():
    driver = Driver(b"wrong")
    with pytest.raises(ValueError, match="mismatch"):
        build_ordered_verified_sftp_probe(lambda _: driver).inspect(config(b"right"))
    assert "authenticate" not in driver.calls
    assert "sftp" not in driver.calls
    assert driver.calls[-1] == "close"


def test_handshake_error_closes_without_authenticating():
    class BrokenDriver(Driver):
        def negotiate_without_authentication(self):
            raise OSError("handshake failed")

    driver = BrokenDriver(b"right")
    with pytest.raises(OSError):
        build_ordered_verified_sftp_probe(lambda _: driver).inspect(config(b"right"))
    assert driver.calls == ["close"]
