"""Bounded, read-only local RGB/thermal previews from project-scoped SQLite evidence."""
from io import BytesIO
from pathlib import Path
import os

from PIL import Image
import pytest

from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.services.review_image_preview import (
    MAX_IMAGE_BYTES, _name_from_stored_source, preview_pending_finding_images,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def sample(tmp_path, *, rgb_link=True, rgb_name="V.JPG", thermal_name="T.JPG"):
    root = tmp_path / "flight"
    root.mkdir()
    database = ProjectDatabase(tmp_path / "review.sqlite3")
    database.initialize()
    database.create_project("P1", "Private Solar")
    database.create_project("P2", "Other Solar")
    with database.connect() as db:
        for project in ("P1", "P2"):
            db.execute(
                "INSERT INTO thermal_frames"
                "(project_id,frame_id,source_file,thermal_source,metadata_json)"
                " VALUES (?,?,?,?,?)",
                (project, "T1", "C:\\PRIVATE\\DJI\\" + thermal_name, "raw", "{}"),
            )
            db.execute(
                "INSERT INTO image_frames"
                "(project_id,frame_id,source_file,metadata_json) VALUES (?,?,?,?)",
                (project, "V1", "D:/SECRET/FLIGHT/" + rgb_name, "{}"),
            )
            db.execute(
                "INSERT INTO findings"
                "(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,"
                "reviewer_status,metadata_json) VALUES (?,?,?,?,?,?,?)",
                (project, "F1", "T1", 6, 8, "unreviewed", "{}"),
            )
            if rgb_link and project == "P1":
                db.execute(
                    "INSERT INTO finding_sensor_links("
                    "project_id,finding_id,rgb_frame_id,transform_method,"
                    "transform_validated,status) VALUES (?,?,?,?,?,?)",
                    (project, "F1", "V1", "none", 0, "linked"),
                )
    return ProjectApplicationService(database), root


def write_image(path, *, color, size=(1200, 800), file_format="JPEG"):
    Image.new("RGB", size, color).save(path, format=file_format)


def decoded(payload):
    with Image.open(BytesIO(payload)) as image:
        assert image.format == "PNG"
        assert image.width <= 640
        assert image.height <= 420
        return image.getpixel((0, 0))


def test_explicit_selected_folder_displays_only_project_linked_images(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(200, 25, 25))
    write_image(root / "V.JPG", color=(25, 100, 180))
    thermal, rgb = service.preview_review_images("P1", "F1", root)
    assert thermal is not None and rgb is not None
    assert decoded(thermal)[0] > decoded(thermal)[1]
    assert decoded(rgb)[2] > decoded(rgb)[0]
    # Shared candidate/frame IDs do not make an RGB link in another project.
    other_thermal, other_rgb = service.preview_review_images("P2", "F1", root)
    assert other_thermal is not None
    assert other_rgb is None


def test_never_follow_persisted_absolute_paths_or_read_other_folders(tmp_path):
    service, root = sample(tmp_path)
    secret = tmp_path / "SECRET-T.JPG"
    write_image(secret, color=(255, 0, 0))
    assert service.preview_review_images("P1", "F1", root) == (None, None)
    assert secret.is_file()
    assert _name_from_stored_source("C:\\PRIVATE\\DJI\\T.JPG") == "T.JPG"
    assert _name_from_stored_source("../../private/T.JPG") == "T.JPG"
    assert _name_from_stored_source("C:\\PRIVATE\\DJI\\..") is None
    assert _name_from_stored_source("evil:stream.JPG") is None


def test_missing_and_invalid_requests_do_not_show_unrelated_frames(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(15, 30, 45))
    assert service.preview_review_images("P1", "F1", root)[1] is None
    for project, candidate in (("MISSING", "F1"), ("P1", "MISSING")):
        with pytest.raises((KeyError, ValueError, PermissionError)):
            service.preview_review_images(project, candidate, root)
    with pytest.raises(ValueError, match="active project"):
        preview_pending_finding_images(service.database, "", "F1", root)
    with pytest.raises(ValueError, match="stored finding"):
        preview_pending_finding_images(service.database, "P1", "", root)
    with service.database.connect() as db:
        db.execute(
            "UPDATE findings SET reviewer_status='confirmed'"
            " WHERE project_id='P1' AND finding_id='F1'",
        )
    with pytest.raises(ValueError, match="not pending"):
        preview_pending_finding_images(service.database, "P1", "F1", root)


def test_reject_symlinked_files_and_folders(tmp_path):
    service, root = sample(tmp_path)
    outside = tmp_path / "outside.JPG"
    write_image(outside, color=(10, 20, 30))
    symlink = root / "T.JPG"
    try:
        symlink.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable on this runner")
    with pytest.raises(ValueError, match="links"):
        service.preview_review_images("P1", "F1", root)
    symlink.unlink()
    linked_root = tmp_path / "shortcut"
    linked_root.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic"):
        service.preview_review_images("P1", "F1", linked_root)


def test_reject_non_image_payload_and_wrong_signature(tmp_path):
    service, root = sample(tmp_path)
    (root / "T.JPG").write_bytes(b"<html>not a jpeg</html>")
    with pytest.raises((OSError, ValueError)):
        service.preview_review_images("P1", "F1", root)
    write_image(root / "T.JPG", color=(3, 4, 5), file_format="PNG")
    # Extension is not proof of the media type: only verified JPEG/PNG content.
    png, missing = service.preview_review_images("P1", "F1", root)
    assert decoded(png) == (3, 4, 5)
    assert missing is None


def test_reject_oversized_images_before_decode_and_ambiguous_pair(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(20, 30, 40))
    with (root / "T.JPG").open("ab") as fd:
        fd.truncate(MAX_IMAGE_BYTES + 1)
    with pytest.raises(ValueError, match="unsupported"):
        service.preview_review_images("P1", "F1", root)
    with service.database.connect() as db:
        db.execute(
            "UPDATE image_frames SET source_file='T.JPG' "
            "WHERE project_id='P1' AND frame_id='V1'",
        )
    with pytest.raises(ValueError, match="ambiguous"):
        service.preview_review_images("P1", "F1", root)


def test_no_network_or_relative_paths(tmp_path, monkeypatch):
    service, root = sample(tmp_path)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="absolute"):
        preview_pending_finding_images(service.database, "P1", "F1", "flight")
    with pytest.raises(ValueError, match="existing"):
        preview_pending_finding_images(
            service.database, "P1", "F1", tmp_path / "absent",
        )


def test_successful_preview_does_not_change_sqlite_or_original_bytes(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(70, 80, 90))
    before = (root / "T.JPG").read_bytes()
    with service.database.connect() as db:
        prior = tuple(db.execute(
            "SELECT reviewer_status FROM findings WHERE project_id='P1'",
        ))
        audit = db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0]
    thermal, missing_rgb = service.preview_review_images("P1", "F1", root)
    assert decoded(thermal) == (70, 80, 90)
    assert missing_rgb is None
    assert (root / "T.JPG").read_bytes() == before
    with service.database.connect() as db:
        assert tuple(db.execute(
            "SELECT reviewer_status FROM findings WHERE project_id='P1'",
        )) == prior
        assert db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0] == audit
