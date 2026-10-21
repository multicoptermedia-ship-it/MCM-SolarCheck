"""Structure inspection of public ZIP does not modify customer databases."""
from __future__ import annotations

import json
from hashlib import sha1
from pathlib import Path
import zipfile

from mcm_solarcheck.offline.public_infrared_probe import inspect_pinned_archive


def test_probe_distinguishes_indexed_images_and_unindexed_metadata(tmp_path):
    archive = tmp_path / "2020-02-14_InfraredSolarModules.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("images/1.jpg", b"placeholder")
        zipped.writestr("other-info.txt", "public note")
        zipped.writestr(
            "module_metadata.json",
            json.dumps({"1": {"image_filepath": "images/1.jpg",
                              "anomaly_class": "Cell"}}),
        )
    contents = archive.read_bytes()
    git_blob = sha1(f"blob {len(contents)}\0".encode() + contents).hexdigest()
    result = inspect_pinned_archive(
        archive, expected_blob_sha1=git_blob, expected_size=len(contents),
    )
    assert result["metadata_images"] == 1
    assert result["unreferenced_file_count"] == 1
    assert result["unreferenced_extensions"] == {".txt": 1}
    assert result["unreferenced_examples"] == ["other-info.txt"]
    assert not list(tmp_path.glob("*.sqlite3"))
    assert not (tmp_path / "training-data").exists()
