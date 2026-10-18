"""Provenance manifests bind JPEG and derived NPY bytes, not merely shape."""
import cv2
import numpy as np
import pytest

from mcm_solarcheck.services.flight_rgb_provenance import (
    build_rgb_provenance_record,
    verify_rgb_provenance_manifest,
    write_rgb_provenance_manifest,
)


def test_provenance_manifest_detects_changed_source_and_output(tmp_path):
    source, output, manifest = (tmp_path / name for name in ("a.jpg", "a.npy", "a.provenance.json"))
    assert cv2.imwrite(str(source), np.zeros((4, 5, 3), dtype=np.uint8))
    np.save(output, np.zeros((4, 5, 3), dtype=np.uint8))
    record = build_rgb_provenance_record(source, output)
    write_rgb_provenance_manifest(record, manifest)
    assert verify_rgb_provenance_manifest(source, output, manifest)
    with pytest.raises(ValueError):
        write_rgb_provenance_manifest(record, manifest)
    np.save(output, np.ones((4, 5, 3), dtype=np.uint8))
    assert not verify_rgb_provenance_manifest(source, output, manifest)
    assert "a.jpg" not in manifest.read_text()


def test_missing_or_corrupt_manifest_is_not_trusted(tmp_path):
    source, output, manifest = (tmp_path / name for name in ("a.jpg", "a.npy", "a.provenance.json"))
    assert cv2.imwrite(str(source), np.zeros((4, 5, 3), dtype=np.uint8))
    np.save(output, np.zeros((4, 5, 3), dtype=np.uint8))
    assert not verify_rgb_provenance_manifest(source, output, manifest)
    manifest.write_text("not json")
    assert not verify_rgb_provenance_manifest(source, output, manifest)
