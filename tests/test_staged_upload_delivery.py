from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.local_staged_upload_backend import LocalStagedUploadBackend
from mcm_solarcheck.services.staged_upload_delivery import StagedUploadDelivery


def test_verified_upload_published_after_staging(tmp_path):
    delivery = StagedUploadDelivery(LocalStagedUploadBackend(tmp_path))
    receipt = delivery.deliver("customer/project/rgb.jpg", b"image")
    assert receipt.size_bytes == 5
    assert receipt.sha256_hex == sha256(b"image").hexdigest()
    assert (tmp_path / receipt.final_key).read_bytes() == b"image"
    assert list((tmp_path / ".staging").iterdir()) == []


def test_existing_published_file_is_never_overwritten(tmp_path):
    delivery = StagedUploadDelivery(LocalStagedUploadBackend(tmp_path))
    delivery.deliver("customer/project/rgb.jpg", b"first")
    with pytest.raises(FileExistsError):
        delivery.deliver("customer/project/rgb.jpg", b"second")
    assert (tmp_path / "customer/project/rgb.jpg").read_bytes() == b"first"


def test_unsafe_final_key_rejected(tmp_path):
    delivery = StagedUploadDelivery(LocalStagedUploadBackend(tmp_path))
    with pytest.raises(ValueError):
        delivery.deliver("../outside", b"image")
