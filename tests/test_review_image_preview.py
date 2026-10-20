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
                "finding_type,reviewer_status,metadata_json) VALUES (?,?,?,?,?,?,?,?)",
                (project, "F1", "T1", 6, 8, "thermal_anomaly_candidate", "unreviewed", "{}"),
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


def stored_checksum(service, project, frame_id, modality, digest):
    """Create synthetic import-time provenance, not a training approval."""
    with service.database.connect() as db:
        db.execute(
            "INSERT INTO training_samples "
            "(sample_id, project_id, source_frame_id, source_file, modality, "
            "content_sha256, label_status, rights_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                modality + ":" + project + ":" + frame_id, project, frame_id,
                "/synthetic/import/" + frame_id + ".JPG", modality, digest,
                "unlabeled", "unverified",
            ),
        )


def test_import_sha256_binds_original_rgb_and_thermal_bytes(tmp_path):
    """Both matched files show only the verifiable import-time digest status."""
    from hashlib import sha256

    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(30, 80, 140))
    write_image(root / "V.JPG", color=(120, 10, 50))
    thermal_digest = sha256((root / "T.JPG").read_bytes()).hexdigest()
    rgb_digest = sha256((root / "V.JPG").read_bytes()).hexdigest()
    stored_checksum(service, "P1", "T1", "thermal", thermal_digest)
    stored_checksum(service, "P1", "V1", "rgb", rgb_digest)
    evidence = service.preview_review_image_evidence("P1", "F1", root)
    assert evidence.thermal_integrity == "verified"
    assert evidence.rgb_integrity == "verified"
    assert decoded(evidence.thermal_png)[2] > decoded(evidence.thermal_png)[0]
    assert decoded(evidence.rgb_png)[0] > decoded(evidence.rgb_png)[1]
    assert service.preview_review_images("P1", "F1", root) == (
        evidence.thermal_png, evidence.rgb_png,
    )
    # Same filename and unchanged dimensions are not sufficient.
    write_image(root / "T.JPG", color=(31, 80, 140))
    changed = service.preview_review_image_evidence("P1", "F1", root)
    assert changed.thermal_png is None
    assert changed.thermal_integrity == "mismatch"
    assert changed.rgb_integrity == "verified"
    assert changed.rgb_png == evidence.rgb_png
    assert service.preview_review_images("P1", "F1", root) == (
        None, evidence.rgb_png,
    )


def test_digest_is_scoped_to_project_and_modality(tmp_path):
    from hashlib import sha256

    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(20, 40, 60))
    write_image(root / "V.JPG", color=(60, 40, 20))
    thermal_digest = sha256((root / "T.JPG").read_bytes()).hexdigest()
    rgb_digest = sha256((root / "V.JPG").read_bytes()).hexdigest()
    # P1 knows only an RGB fingerprint. No thermal fingerprint is fabricated.
    stored_checksum(service, "P1", "V1", "rgb", rgb_digest)
    # P2 has the same thermal frame ID but an intentionally different digest.
    stored_checksum(service, "P2", "T1", "thermal", "f" * 64)
    p1 = service.preview_review_image_evidence("P1", "F1", root)
    assert p1.thermal_integrity == "unverified"
    assert p1.rgb_integrity == "verified"
    assert p1.thermal_png is not None and p1.rgb_png is not None
    p2 = service.preview_review_image_evidence("P2", "F1", root)
    assert p2.thermal_integrity == "mismatch"
    assert p2.thermal_png is None
    assert p2.rgb_integrity == "unavailable"
    assert p2.rgb_png is None
    assert service.preview_review_images("P1", "F1", root)[0] is not None
    # Use the actual import digest for P2 after removing its wrong provenance.
    with service.database.connect() as db:
        db.execute(
            "UPDATE training_samples SET content_sha256=? "
            "WHERE project_id=? AND source_frame_id=? AND modality=?",
            (thermal_digest, "P2", "T1", "thermal"),
        )
    verified = service.preview_review_image_evidence("P2", "F1", root)
    assert verified.thermal_integrity == "verified"
    assert verified.thermal_png is not None


def test_invalid_or_incomplete_stored_sha_cannot_authorize_a_preview(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(55, 65, 75))
    stored_checksum(service, "P1", "T1", "thermal", "not-a-digest")
    result = service.preview_review_image_evidence("P1", "F1", root)
    assert result.thermal_png is None
    assert result.thermal_integrity == "mismatch"
    assert result.rgb_png is None
    assert result.rgb_integrity == "unavailable"


def test_no_recorded_sha_does_not_get_false_verification_badge(tmp_path):
    service, root = sample(tmp_path, rgb_link=False)
    write_image(root / "T.JPG", color=(101, 111, 121))
    result = service.preview_review_image_evidence("P1", "F1", root)
    assert result.thermal_integrity == "unverified"
    assert decoded(result.thermal_png) == (101, 111, 121)
    assert result.rgb_integrity == "unavailable"
    assert result.rgb_png is None
    assert not hasattr(result, "customer_path")


def test_checksum_gating_never_writes_review_or_source_files(tmp_path):
    from hashlib import sha256

    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(11, 21, 31))
    before_bytes = (root / "T.JPG").read_bytes()
    stored_checksum(service, "P1", "T1", "thermal", sha256(before_bytes).hexdigest())
    with service.database.connect() as db:
        n_before = db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0]
    result = service.preview_review_image_evidence("P1", "F1", root)
    assert result.thermal_integrity == "verified"
    assert (root / "T.JPG").read_bytes() == before_bytes
    with service.database.connect() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id='P1'",
        ).fetchone()[0] == n_before
        assert db.execute(
            "SELECT reviewer_status FROM findings WHERE project_id='P1' "
            "AND finding_id='F1'",
        ).fetchone()[0] == "unreviewed"


def set_matching_thermal_geometry(service, project="P1", *, size=(1200, 800), point=(600, 400)):
    with service.database.connect() as db:
        db.execute(
            "UPDATE thermal_frames SET width=?, height=? "
            "WHERE project_id=? AND frame_id='T1'",
            (*size, project),
        )
        db.execute(
            "UPDATE findings SET pixel_x=?, pixel_y=? "
            "WHERE project_id=? AND finding_id='F1'",
            (*point, project),
        )


def set_matching_rgb_geometry(service, *, size=(1200, 800), point=(600.0, 400.0), validated=1):
    with service.database.connect() as db:
        db.execute(
            "UPDATE image_frames SET width=?, height=? "
            "WHERE project_id='P1' AND frame_id='V1'",
            size,
        )
        db.execute(
            "UPDATE finding_sensor_links SET rgb_pixel_x=?, rgb_pixel_y=?, "
            "transform_validated=? WHERE project_id='P1' AND finding_id='F1'",
            (*point, validated),
        )


def preview_center_color(png):
    with Image.open(BytesIO(png)) as image:
        return image.getpixel((image.width // 2, image.height // 2))


def test_thermal_marker_uses_real_saved_pixel_only_at_matching_dimensions(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(90, 100, 110))
    baseline = service.preview_review_image_evidence("P1", "F1", root)
    assert baseline.thermal_marker == "different_geometry"
    assert preview_center_color(baseline.thermal_png) != (57, 243, 189)

    set_matching_thermal_geometry(service)
    located = service.preview_review_image_evidence("P1", "F1", root)
    assert located.thermal_marker == "marked"
    assert preview_center_color(located.thermal_png) == (57, 243, 189)
    assert located.thermal_integrity == "unverified"
    assert located.rgb_marker == "unavailable"
    # A locator never updates inspection conclusions or original bytes.
    assert service.import_summary("P1").unreviewed_findings == 1


def test_rgb_marker_requires_validated_transform_and_native_dimensions(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(90, 100, 110))
    write_image(root / "V.JPG", color=(50, 60, 70))
    set_matching_rgb_geometry(service, validated=0)
    not_validated = service.preview_review_image_evidence("P1", "F1", root)
    assert not_validated.rgb_marker == "unvalidated"
    assert preview_center_color(not_validated.rgb_png) != (57, 243, 189)
    set_matching_rgb_geometry(service, validated=1)
    validated = service.preview_review_image_evidence("P1", "F1", root)
    assert validated.rgb_marker == "marked"
    assert preview_center_color(validated.rgb_png) == (57, 243, 189)
    assert validated.thermal_marker == "different_geometry"
    assert service.preview_review_image_evidence("P2", "F1", root).rgb_marker == "unavailable"


def test_mismatched_native_geometry_and_out_of_bounds_pixel_never_mark(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(31, 41, 51))
    set_matching_thermal_geometry(service, size=(640, 512))
    wrong_dimensions = service.preview_review_image_evidence("P1", "F1", root)
    assert wrong_dimensions.thermal_marker == "different_geometry"
    assert preview_center_color(wrong_dimensions.thermal_png) != (57, 243, 189)
    set_matching_thermal_geometry(service, point=(1200, 10))
    outside = service.preview_review_image_evidence("P1", "F1", root)
    assert outside.thermal_marker == "different_geometry"
    set_matching_thermal_geometry(service, size=(1200, 800), point=(1200, 10))
    outside = service.preview_review_image_evidence("P1", "F1", root)
    assert outside.thermal_marker == "outside"
    with service.database.connect() as db:
        db.execute(
            "UPDATE findings SET pixel_x=-1, pixel_y=0 "
            "WHERE project_id='P1' AND finding_id='F1'"
        )
    negative = service.preview_review_image_evidence("P1", "F1", root)
    assert negative.thermal_marker == "outside"


def test_exif_rotated_thermal_jpeg_is_not_marked_without_coordinate_transform(tmp_path):
    service, root = sample(tmp_path)
    set_matching_thermal_geometry(service)
    rotated = Image.new("RGB", (1200, 800), (26, 36, 46))
    exif = Image.Exif()
    exif[274] = 6
    rotated.save(root / "T.JPG", format="JPEG", exif=exif)
    evidence = service.preview_review_image_evidence("P1", "F1", root)
    assert evidence.thermal_marker == "orientation"
    assert evidence.thermal_png is not None
    assert preview_center_color(evidence.thermal_png) != (57, 243, 189)


def test_mismatched_sha_blocks_image_and_locator_even_if_geometry_matches(tmp_path):
    service, root = sample(tmp_path)
    write_image(root / "T.JPG", color=(25, 35, 45))
    set_matching_thermal_geometry(service)
    stored_checksum(service, "P1", "T1", "thermal", "0" * 64)
    result = service.preview_review_image_evidence("P1", "F1", root)
    assert result.thermal_integrity == "mismatch"
    assert result.thermal_marker == "unavailable"
    assert result.thermal_png is None
