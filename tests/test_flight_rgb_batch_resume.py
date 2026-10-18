"""Resume inspection is conservative and never modifies existing outputs."""
import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_batch_resume import inspect_rgb_batch_resume


def test_resume_reports_missing_and_shape_valid_but_unverified(tmp_path):
    source = tmp_path / "a.jpg"
    assert cv2.imwrite(str(source), np.zeros((4, 5, 3), dtype=np.uint8))
    output = tmp_path / "derived"
    output.mkdir()
    initial = inspect_rgb_batch_resume([source], output)
    assert initial["entries"][0]["status"] == "missing"
    assert initial["safe_to_resume_automatically"]
    array = output / "a.npy"
    np.save(array, np.zeros((4, 5, 3), dtype=np.uint8))
    original = array.read_bytes()
    result = inspect_rgb_batch_resume([source], output)
    assert result["entries"][0]["status"] == "existing_shape_valid"
    assert result["existing_outputs_unverified_provenance"]
    assert not result["safe_to_resume_automatically"]
    assert array.read_bytes() == original


def test_resume_reports_corrupt_existing_output(tmp_path):
    source = tmp_path / "a.jpg"
    assert cv2.imwrite(str(source), np.zeros((4, 5, 3), dtype=np.uint8))
    output = tmp_path / "derived"
    output.mkdir()
    (output / "a.npy").write_bytes(b"not a numpy array")
    result = inspect_rgb_batch_resume([source], output)
    assert result["entries"][0]["status"] == "invalid"
    assert not result["safe_to_resume_automatically"]


def test_resume_recognizes_hash_verified_provenance(tmp_path):
    from mcm_solarcheck.services.flight_rgb_provenance import (
        build_rgb_provenance_record, write_rgb_provenance_manifest,
    )
    source = tmp_path / "a.jpg"
    assert cv2.imwrite(str(source), np.zeros((4, 5, 3), dtype=np.uint8))
    output = tmp_path / "derived"
    output.mkdir()
    array = output / "a.npy"
    np.save(array, np.zeros((4, 5, 3), dtype=np.uint8))
    write_rgb_provenance_manifest(
        build_rgb_provenance_record(source, array),
        output / "a.provenance.json",
    )
    result = inspect_rgb_batch_resume([source], output)
    assert result["entries"][0]["status"] == "verified_provenance"
    assert result["verified_outputs"] == 1
    assert not result["safe_to_resume_automatically"]
    source.write_bytes(b"modified source")
    with pytest.raises(ValueError):
        inspect_rgb_batch_resume([source], output)
