import pytest

from mcm_solarcheck.infrastructure.sftp_capability_policy import (
    SFTPCapabilities, SFTPCapabilityPolicy,
)
from mcm_solarcheck.infrastructure.sftp_storage_config import SFTPStorageConfig
from mcm_solarcheck.infrastructure.sftp_read_only_probe import SFTPReadOnlyProbe


def test_sftp_config_requires_pinned_host_key_and_private_root():
    with pytest.raises(ValueError):
        SFTPStorageConfig("example.test", 22, "operator", "/", "SHA256:abc")
    with pytest.raises(ValueError):
        SFTPStorageConfig("example.test", 22, "operator", "/private", "")
    config = SFTPStorageConfig("example.test", 22, "operator", "/private", "SHA256:abcdefghijklmnopqrstuvwxyz")
    assert config.port == 22


def test_sftp_capabilities_default_to_no_writes_or_publish():
    policy = SFTPCapabilityPolicy(SFTPCapabilities())
    assert not policy.allow_immutable_part_write()
    assert not policy.allow_final_publication()
    assert SFTPCapabilityPolicy(SFTPCapabilities(exclusive_create_verified=True)).allow_immutable_part_write()
    assert not SFTPCapabilityPolicy(SFTPCapabilities(exclusive_publish_verified=True)).allow_final_publication()


def test_read_only_probe_requires_verified_connector():
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def directory_exists(self, root):
            return root == "/private"

    class Connector:
        def open_verified_read_only(self, config):
            assert config.root == "/private"
            return Session()

    config = SFTPStorageConfig("example.test", 22, "operator", "/private", "SHA256:abcdefghijklmnopqrstuvwxyz")
    assert SFTPReadOnlyProbe(Connector()).inspect(config) == {
        "root_exists": True, "host_key_verified": True
    }
