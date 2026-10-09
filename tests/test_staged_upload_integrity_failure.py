import pytest

from mcm_solarcheck.infrastructure.local_staged_upload_backend import LocalStagedUploadBackend
from mcm_solarcheck.services.staged_upload_delivery import StagedUploadDelivery


class CorruptingBackend(LocalStagedUploadBackend):
    def read_staging(self, key):
        return b"corrupted"


def test_corrupt_staging_never_published(tmp_path):
    delivery = StagedUploadDelivery(CorruptingBackend(tmp_path))
    with pytest.raises(ValueError, match="integrity mismatch"):
        delivery.deliver("c/p/thermal.tiff", b"original")
    assert not (tmp_path / "c/p/thermal.tiff").exists()
    assert list((tmp_path / ".staging").iterdir()) == []


class PublishFailureBackend(LocalStagedUploadBackend):
    def publish(self, staging_key, final_key):
        raise OSError("simulated publish failure")


def test_failed_publish_cleans_staging(tmp_path):
    delivery = StagedUploadDelivery(PublishFailureBackend(tmp_path))
    with pytest.raises(OSError):
        delivery.deliver("c/p/rgb.jpg", b"image")
    assert not (tmp_path / "c/p/rgb.jpg").exists()
    assert list((tmp_path / ".staging").iterdir()) == []
