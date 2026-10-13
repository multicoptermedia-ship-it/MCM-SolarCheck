import pytest

from mcm_solarcheck.infrastructure.sftp_staged_upload_backend import (
    SFTPStagedUploadBackend, SFTPPublishUnsupported,
)
from mcm_solarcheck.services.staged_upload_delivery import StagedUploadDelivery


class NoExclusivePublish:
    def __init__(self):
        self.files = {}

    def write_exclusive(self, path, data):
        self.files[path] = data

    def read(self, path):
        return self.files[path]

    def remove(self, path):
        self.files.pop(path, None)


def test_transport_without_exclusive_publish_fails_closed():
    transport = NoExclusivePublish()
    delivery = StagedUploadDelivery(SFTPStagedUploadBackend(transport, root="/private"))
    with pytest.raises(SFTPPublishUnsupported):
        delivery.deliver("c/p/image.jpg", b"image")
    assert transport.files == {}


@pytest.mark.parametrize("key", ["../escape", "/absolute", "a//b", "a/./b", "a/../b"])
def test_unsafe_keys_rejected(key):
    backend = SFTPStagedUploadBackend(NoExclusivePublish(), root="/private")
    with pytest.raises(ValueError):
        backend.read_staging(key)


@pytest.mark.parametrize("root", ["", "/", "relative", "/a/../b"])
def test_unsafe_roots_rejected(root):
    with pytest.raises(ValueError):
        SFTPStagedUploadBackend(NoExclusivePublish(), root=root)
