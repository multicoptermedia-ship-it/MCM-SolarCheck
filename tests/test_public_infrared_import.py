"""Pinned public infrared archive intake, license and safety boundary tests."""
from __future__ import annotations

from hashlib import sha1, sha256
from io import BytesIO
import json
from pathlib import Path
import stat
import zipfile

from PIL import Image
import pytest

from mcm_solarcheck.offline.public_infrared_import import (
    _pinned_archive_identity, import_raptor_maps_zip,
)
from mcm_solarcheck.services.pv_public_infrared_source import (
    ARCHIVE_GIT_BLOB_SHA1, ARCHIVE_NAME, ARCHIVE_SIZE, ARCHIVE_URL, DATASET_ID,
    LICENSE_URL, ORIGINAL_CLASSES, RaptorImportAuthorization, UPSTREAM_COMMIT,
    unreviewed_license_record,
)


def _jpeg(*, dimensions=(24, 40)):
    buf = BytesIO()
    Image.new("L", dimensions, color=80).save(buf, format="JPEG")
    return buf.getvalue()


def _archive(tmp_path, *, labels=None, files=None, extra=None, prefix="InfraredSolarModules/"):
    root = tmp_path / ARCHIVE_NAME
    labels = labels if labels is not None else {"1": "No-Anomaly", "2": "Cell"}
    files = files if files is not None else {key: _jpeg() for key in labels}
    data = {
        key: {"image_filepath": f"images/{key}.jpg", "anomaly_class": label}
        for key, label in labels.items()
    }
    with zipfile.ZipFile(root, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        # Legitimate directory records are common in upstream ZIP archives.
        zipped.writestr(prefix, "")
        zipped.writestr(prefix + "images/", "")
        zipped.writestr(prefix + "module_metadata.json", json.dumps(data))
        for key, contents in files.items():
            zipped.writestr(prefix + f"images/{key}.jpg", contents)
        for name, content in (extra or {}).items():
            zipped.writestr(name, content)
    blob = root.read_bytes()
    git_blob = sha1(f"blob {len(blob)}\0".encode("ascii") + blob).hexdigest()
    return root, git_blob


def _approval():
    return RaptorImportAuthorization(
        "Human rights reviewer", LICENSE_URL, True,
    )


def _ingest(tmp_path, archive, hash_value, *, approval=None):
    return import_raptor_maps_zip(
        archive, tmp_path / "private-research", _approval() if approval is None else approval,
        expected_blob_sha1=hash_value, expected_size=archive.stat().st_size,
    )


def test_real_source_is_pinned_without_embedding_binary():
    assert len(ARCHIVE_GIT_BLOB_SHA1) == 40
    assert ARCHIVE_SIZE == 15_495_990
    assert UPSTREAM_COMMIT in ARCHIVE_URL
    assert ARCHIVE_NAME in ARCHIVE_URL
    assert set(ORIGINAL_CLASSES) == {
        "Cell", "Cell-Multi", "Cracking", "Hot-Spot", "Hot-Spot-Multi",
        "Shadowing", "Diode", "Diode-Multi", "Vegetation", "Soiling",
        "Offline-Module", "No-Anomaly",
    }
    record = unreviewed_license_record()
    assert record.dataset_id == DATASET_ID
    assert not record.can_train_commercially(record.modality)
    with pytest.raises(PermissionError):
        RaptorImportAuthorization("reviewer", LICENSE_URL, False)


def test_local_original_archive_import_keeps_all_labels_and_source_hashes(tmp_path):
    archive, git_blob = _archive(tmp_path)
    outcome = _ingest(tmp_path, archive, git_blob)
    assert outcome["images"] == 2
    assert outcome["counts"] == {"Cell": 1, "No-Anomaly": 1}
    assert outcome["sha256"] == sha256(archive.read_bytes()).hexdigest()
    folder = tmp_path / "private-research"
    record = json.loads((folder / "public-infrared-index.json").read_text())
    assert record["status"] == "exploratory_only_not_approved_for_reports"
    assert record["site_grouping"] == "not_available_no_site_disjoint_validation"
    assert record["dataset_id"] == DATASET_ID
    assert record["license_claim"] == "MIT in upstream repository"
    assert record["reviewer"] == "Human rights reviewer"
    assert [x["class"] for x in record["samples"]] == ["No-Anomaly", "Cell"]
    assert all((folder / x["image"]).is_file() for x in record["samples"])
    assert all(
        sha256((folder / x["image"]).read_bytes()).hexdigest() == x["sha256"]
        for x in record["samples"]
    )
    assert not (tmp_path / "solarcheck.sqlite3").exists()
    assert "training_running" not in (folder / "public-infrared-index.json").read_text()


def test_tampered_github_archive_rejected_before_writing(tmp_path):
    archive, h = _archive(tmp_path)
    original = archive.read_bytes()
    archive.write_bytes(original + b"changed")
    with pytest.raises(PermissionError, match="size"):
        _ingest(tmp_path, archive, h)
    assert not (tmp_path / "private-research").exists()
    with pytest.raises(PermissionError, match="Git blob"):
        import_raptor_maps_zip(
            archive, tmp_path / "private-research", _approval(),
            expected_blob_sha1=h, expected_size=len(original) + len(b"changed"),
        )


@pytest.mark.parametrize("damage", [
    "missing_image", "unlisted_image", "unknown_class", "wrong_size",
    "zip_slip", "duplicate", "invalid_jpeg", "absolute_path",
])
def test_bad_metadata_images_and_zip_entries_cannot_publish(tmp_path, damage):
    kwargs = {}
    if damage == "missing_image":
        kwargs["files"] = {"1": _jpeg()}
    if damage == "unlisted_image":
        kwargs["files"] = {"1": _jpeg(), "2": _jpeg(), "3": _jpeg()}
    if damage == "unknown_class":
        kwargs["labels"] = {"1": "No-Anomaly", "2": "MADE_UP_THERMAL_FAILURE"}
    if damage == "wrong_size":
        kwargs["files"] = {"1": _jpeg(dimensions=(16, 16)), "2": _jpeg()}
    if damage == "zip_slip":
        kwargs["extra"] = {"../evil.txt": b"outside"}
    if damage == "duplicate":
        kwargs["extra"] = {"InfraredSolarModules/images/1.jpg": _jpeg()}
    if damage == "invalid_jpeg":
        kwargs["files"] = {"1": b"not a JPEG", "2": _jpeg()}
    if damage == "absolute_path":
        kwargs["extra"] = {"/outside.txt": b"outside"}
    archive, git_blob = _archive(tmp_path, **kwargs)
    with pytest.raises((PermissionError, ValueError, OSError)):
        _ingest(tmp_path, archive, git_blob)
    assert not (tmp_path / "private-research").exists()


def test_archived_symlink_rejected_before_extraction(tmp_path):
    archive, _ = _archive(tmp_path)
    with zipfile.ZipFile(archive, "a") as zipped:
        link = zipfile.ZipInfo("InfraredSolarModules/images/linked.jpg")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        zipped.writestr(link, "1.jpg")
    blob = archive.read_bytes()
    expected = sha1(f"blob {len(blob)}\0".encode() + blob).hexdigest()
    with pytest.raises(PermissionError, match="symlink"):
        _ingest(tmp_path, archive, expected)


def test_existing_target_and_unchecked_rights_are_never_overwritten(tmp_path):
    archive, hash_value = _archive(tmp_path)
    target = tmp_path / "private-research"
    target.mkdir()
    (target / "keep.txt").write_text("original")
    with pytest.raises(PermissionError):
        _ingest(tmp_path, archive, hash_value)
    assert (target / "keep.txt").read_text() == "original"
    target.rename(tmp_path / "prior")
    with pytest.raises(PermissionError):
        import_raptor_maps_zip(
            archive, target,
            RaptorImportAuthorization("reviewer", LICENSE_URL, False),
            expected_blob_sha1=hash_value, expected_size=archive.stat().st_size,
        )
    assert not target.exists()


def test_original_git_archive_identity_requires_exact_expected_filename(tmp_path):
    archive, digest = _archive(tmp_path)
    assert len(_pinned_archive_identity(archive, digest, archive.stat().st_size)) == 64
    other = tmp_path / "untrusted.zip"
    archive.rename(other)
    with pytest.raises(PermissionError):
        _pinned_archive_identity(other, digest, other.stat().st_size)


def test_no_importer_requests_training_or_fetches_internet():
    import inspect
    from mcm_solarcheck.offline import public_infrared_import
    source = inspect.getsource(public_infrared_import)
    assert "urllib.request" not in source
    assert "requests.get(" not in source
    assert "httpx." not in source
    assert "offline_training_jobs" not in source
    assert "approve_offline_report(" not in source
