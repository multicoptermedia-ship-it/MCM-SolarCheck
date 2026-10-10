import pytest

from mcm_solarcheck.infrastructure.sftp_staged_upload_backend import SFTPStagedUploadBackend
from mcm_solarcheck.services.staged_upload_delivery import StagedUploadDelivery


class MemoryTransport:
    def __init__(self):
        self.files = {}

    def write_exclusive(self, path, data):
        if path in self.files:
            raise FileExistsError(path)
        self.files[path] = data

    def read(self, path):
        return self.files[path]

    def remove(self, path):
        self.files.pop(path, None)

    def publish_exclusive(self, source, destination):
        if destination in self.files:
            raise FileExistsError(destination)
        self.files[destination] = self.files.pop(source)


def test_sftp_delivery_publishes_only_verified_content():
    transport = MemoryTransport()
    delivery = StagedUploadDelivery(SFTPStagedUploadBackend(transport, root="/private/uploads"))
    receipt = delivery.deliver("customer/project/rgb.jpg", b"rgb")
    assert transport.files == {"/private/uploads/customer/project/rgb.jpg": b"rgb"}
    assert receipt.size_bytes == 3


def test_sftp_delivery_does_not_replace_existing_object():
    transport = MemoryTransport()
    delivery = StagedUploadDelivery(SFTPStagedUploadBackend(transport, root="/private/uploads"))
    delivery.deliver("c/p/rgb.jpg", b"first")
    with pytest.raises(FileExistsError):
        delivery.deliver("c/p/rgb.jpg", b"second")
    assert transport.files["/private/uploads/c/p/rgb.jpg"] == b"first"
