import pytest

from mcm_solarcheck.infrastructure.sftp_host_key_pin import (
    ssh_sha256_fingerprint, verify_ssh_host_key,
)
from mcm_solarcheck.infrastructure.sftp_storage_config import SFTPStorageConfig
from mcm_solarcheck.infrastructure.verified_read_only_sftp_connector import VerifiedReadOnlySFTPConnector


class FakeClient:
    def __init__(self, key):
        self.key = key
        self.closed = False
        self.opened = False

    def negotiated_host_key_blob(self):
        return self.key

    def open_read_only_sftp(self):
        self.opened = True
        return self

    def directory_exists(self, path):
        return path == "/private"

    def close(self):
        self.closed = True


def config(key):
    return SFTPStorageConfig("example.test", 22, "user", "/private", ssh_sha256_fingerprint(key))


def test_verified_key_allows_read_only_session_and_closes_client():
    client = FakeClient(b"expected-key")
    connector = VerifiedReadOnlySFTPConnector(lambda _: client)
    with connector.open_verified_read_only(config(b"expected-key")) as session:
        assert session.directory_exists("/private")
    assert client.opened
    assert client.closed


def test_mismatched_key_never_opens_sftp_and_closes_client():
    client = FakeClient(b"unexpected-key")
    connector = VerifiedReadOnlySFTPConnector(lambda _: client)
    with pytest.raises(ValueError, match="mismatch"):
        connector.open_verified_read_only(config(b"expected-key"))
    assert not client.opened
    assert client.closed


def test_fingerprint_verification_rejects_wrong_key():
    with pytest.raises(ValueError):
        verify_ssh_host_key(b"wrong", ssh_sha256_fingerprint(b"right"))
