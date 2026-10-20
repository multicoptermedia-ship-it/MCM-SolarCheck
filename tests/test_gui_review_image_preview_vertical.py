"""End-to-end Qt review image preview: explicit local folder to SQLite-bound frames.

Synthetic JPEGs only, no DJI authenticity, radiometry or Windows hardware claim.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PIL import Image
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QListWidget, QPushButton

from mcm_solarcheck.gui.review_page import make_review_page
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def seeded_window(tmp_path):
    window = build_offline_window(tmp_path / "flight.sqlite3")
    service = window._project_service
    for project in ("P1", "P2"):
        service.create_project(project, "Synthetisches Projekt")
        with service.database.connect() as db:
            db.execute(
                "INSERT INTO thermal_frames "
                "(project_id,frame_id,source_file,thermal_source,metadata_json)"
                " VALUES (?,?,?,?,?)",
                (project, "T1", "C:\\PRIVATE_CLIENT\\T.JPG", "raw", "{}"),
            )
            db.execute(
                "INSERT INTO image_frames "
                "(project_id,frame_id,source_file,metadata_json) VALUES (?,?,?,?)",
                (project, "V1", "D:/PRIVATE_CLIENT/V.JPG", "{}"),
            )
            db.execute(
                "INSERT INTO findings "
                "(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,"
                "finding_type,reviewer_status,metadata_json) VALUES (?,?,?,?,?,?,?,?)",
                (project, "F1", "T1", 15, 20, "thermal_anomaly_candidate", "unreviewed", "{}"),
            )
            if project == "P1":
                db.execute(
                    "INSERT INTO findings "
                    "(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,"
                    "finding_type,reviewer_status,metadata_json) VALUES (?,?,?,?,?,?,?,?)",
                    (project, "F2", "T1", 19, 27, "thermal_anomaly_candidate", "unreviewed", "{}"),
                )
                db.execute(
                    "INSERT INTO finding_sensor_links("
                    "project_id,finding_id,rgb_frame_id,transform_method,"
                    "transform_validated,status) VALUES (?,?,?,?,?,?)",
                    (project, "F1", "V1", "none", 0, "linked"),
                )
    images = tmp_path / "explicit-flight"
    images.mkdir()
    Image.new("RGB", (180, 130), (200, 10, 20)).save(images / "T.JPG")
    Image.new("RGB", (190, 140), (10, 80, 200)).save(images / "V.JPG")
    window._open_project("P1")
    return window, images


def widget(window, klass, name):
    result = window._pages[ShellRoute.REVIEW].findChild(klass, name)
    assert result is not None
    return result


def no_pixmap(widget):
    pixmap = widget.pixmap()
    return pixmap is None or pixmap.isNull()


def audit_count(service, project):
    with service.database.connect() as db:
        return db.execute(
            "SELECT COUNT(*) FROM finding_reviews WHERE project_id=?",
            (project,),
        ).fetchone()[0]


def test_explicit_qt_selection_renders_both_linked_originals_read_only(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    service = window._project_service
    original = (folder / "T.JPG").read_bytes()
    selected = []
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory",
        lambda *args, **kwargs: selected.append(1) or str(folder),
    )
    try:
        window.show_route(ShellRoute.REVIEW)
        choices = widget(window, QListWidget, "pending_review_findings")
        show = widget(window, QPushButton, "review_preview_images_button")
        assert choices.count() == 2
        assert not show.isEnabled()
        assert "kein Bild geladen" in widget(
            window, QLabel, "review_preview_thermal",
        ).text()
        choices.setCurrentRow(0)
        assert show.isEnabled()
        assert selected == []
        assert audit_count(service, "P1") == 0
        show.click()
        assert selected == [1]
        for name in ("review_preview_thermal", "review_preview_rgb"):
            pixmap = widget(window, QLabel, name).pixmap()
            assert pixmap is not None and not pixmap.isNull()
            assert pixmap.width() <= 320 and pixmap.height() <= 210
        message = widget(window, QLabel, "review_preview_images_status").text()
        assert "kein radiometrischer" in message.lower()
        assert "PRIVATE_CLIENT" not in message
        assert str(folder) not in message
        assert (folder / "T.JPG").read_bytes() == original
        assert audit_count(service, "P1") == 0
        assert audit_count(service, "P2") == 0
        assert service.import_summary("P1").unreviewed_findings == 2
    finally:
        window.close()


def test_changing_finding_clears_previous_images_and_blocks_unlinked_rgb(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        choices = widget(window, QListWidget, "pending_review_findings")
        choices.setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert not no_pixmap(widget(window, QLabel, "review_preview_rgb"))
        choices.setCurrentRow(1)
        assert no_pixmap(widget(window, QLabel, "review_preview_rgb"))
        assert "kein Bild geladen" in widget(
            window, QLabel, "review_preview_rgb",
        ).text()
        widget(window, QPushButton, "review_preview_images_button").click()
        assert not no_pixmap(widget(window, QLabel, "review_preview_thermal"))
        assert no_pixmap(widget(window, QLabel, "review_preview_rgb"))
        assert "nicht verfügbar" in widget(
            window, QLabel, "review_preview_rgb",
        ).text()
        assert window._project_service.import_summary("P1").confirmed_findings == 0
    finally:
        window.close()


def test_missing_or_rejected_folder_never_exposes_local_paths(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        choose = widget(window, QPushButton, "review_preview_images_button")
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory", lambda *a, **kw: "",
        )
        choose.click()
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal"))
        alternate = tmp_path / "unrelated-private"
        alternate.mkdir()
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory", lambda *a, **kw: str(alternate),
        )
        choose.click()
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal"))
        status = widget(window, QLabel, "review_preview_images_status").text()
        assert str(alternate) not in status
        assert "PRIVATE_CLIENT" not in status
        assert audit_count(window._project_service, "P1") == 0
    finally:
        window.close()


def test_modal_project_change_rejects_old_preview_even_same_finding_id(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    service = window._project_service
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        original_page = window._pages[ShellRoute.REVIEW]
        def choose_and_switch(*args, **kwargs):
            window._open_project("P2")
            return str(folder)
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory", choose_and_switch,
        )
        original_page.findChild(
            QPushButton, "review_preview_images_button",
        ).click()
        assert window.current_project_id == "P2"
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal"))
        assert no_pixmap(widget(window, QLabel, "review_preview_rgb"))
        assert audit_count(service, "P1") == 0
        assert audit_count(service, "P2") == 0
        assert "PRIVATE_CLIENT" not in widget(
            window, QLabel, "review_preview_images_status",
        ).text()
    finally:
        window.close()


def test_online_or_unbound_review_never_opens_local_preview(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    service = window._project_service
    window.close()
    calls = []
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory",
        lambda *args, **kwargs: calls.append(1) or str(folder),
    )
    unbound = make_review_page()
    try:
        assert not unbound.findChild(
            QPushButton, "review_preview_images_button",
        ).isEnabled()
    finally:
        unbound.close()
    online = SolarCheckMainWindow(
        DeploymentMode.ONLINE, project_service=service,
    )
    try:
        online._open_project("P1")
        assert widget(
            online, QListWidget, "pending_review_findings",
        ).count() == 0
        assert not widget(
            online, QPushButton, "review_preview_images_button",
        ).isEnabled()
        assert online._preview_review_images("P1", "F1", str(folder)) is None
        assert calls == []
        assert audit_count(service, "P1") == 0
    finally:
        online.close()


def test_page_switch_makes_old_finding_preview_callback_invalid(
    qt_app, tmp_path,
):
    window, folder = seeded_window(tmp_path)
    try:
        assert window._preview_review_images("P1", "F1", str(folder)) is not None
        # F1 is on page zero; request another (now empty) page directly.
        window._review_offset = 50
        assert window._preview_review_images("P1", "F1", str(folder)) is None
        assert window._preview_review_images("P2", "F1", str(folder)) is None
        assert audit_count(window._project_service, "P1") == 0
    finally:
        window.close()


def add_original_sha(service, project, frame, modality, data):
    from hashlib import sha256

    digest = sha256(data).hexdigest()
    with service.database.connect() as db:
        db.execute(
            "INSERT INTO training_samples "
            "(sample_id, project_id, source_frame_id, source_file, modality, "
            "content_sha256, label_status, rights_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project + ":" + modality + ":" + frame,
                project, frame, "/synthetic/import/" + frame + ".JPG",
                modality, digest, "unlabeled", "unverified",
            ),
        )


def test_qt_labels_matching_import_hashes_without_automatic_review(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    service = window._project_service
    add_original_sha(service, "P1", "T1", "thermal", (folder / "T.JPG").read_bytes())
    add_original_sha(service, "P1", "V1", "rgb", (folder / "V.JPG").read_bytes())
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        items = widget(window, QListWidget, "pending_review_findings")
        items.setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        for image_name, state_name in (
            ("review_preview_thermal", "review_preview_thermal_integrity"),
            ("review_preview_rgb", "review_preview_rgb_integrity"),
        ):
            image = widget(window, QLabel, image_name)
            assert image.pixmap() is not None and not image.pixmap().isNull()
            status = widget(window, QLabel, state_name).text()
            assert "SHA-256 stimmt" in status
            assert "keine Garantie" in status
            assert "PRIVATE_CLIENT" not in status
            assert str(folder) not in status
        assert audit_count(service, "P1") == 0
        assert service.import_summary("P1").unreviewed_findings == 2
    finally:
        window.close()


def test_qt_blocks_modified_thermal_but_keeps_verified_rgb(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    service = window._project_service
    add_original_sha(service, "P1", "T1", "thermal", (folder / "T.JPG").read_bytes())
    add_original_sha(service, "P1", "V1", "rgb", (folder / "V.JPG").read_bytes())
    Image.new("RGB", (180, 130), (100, 40, 20)).save(folder / "T.JPG")
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        thermal = widget(window, QLabel, "review_preview_thermal")
        rgb = widget(window, QLabel, "review_preview_rgb")
        assert thermal.pixmap() is None or thermal.pixmap().isNull()
        assert "nicht verfügbar" in thermal.text()
        assert rgb.pixmap() is not None and not rgb.pixmap().isNull()
        assert "Abweichende Import-Prüfsumme" in widget(
            window, QLabel, "review_preview_thermal_integrity",
        ).text()
        assert "SHA-256 stimmt" in widget(
            window, QLabel, "review_preview_rgb_integrity",
        ).text()
        assert audit_count(service, "P1") == 0
        assert audit_count(service, "P2") == 0
    finally:
        window.close()


def test_qt_unverified_warnings_clear_on_finding_or_project_change(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        findings = widget(window, QListWidget, "pending_review_findings")
        findings.setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert "Bildidentität nicht überprüfbar" in widget(
            window, QLabel, "review_preview_thermal_integrity",
        ).text()
        assert "Bildidentität nicht überprüfbar" in widget(
            window, QLabel, "review_preview_rgb_integrity",
        ).text()
        findings.setCurrentRow(1)
        assert widget(
            window, QLabel, "review_preview_thermal_integrity",
        ).text() == ""
        assert widget(
            window, QLabel, "review_preview_rgb_integrity",
        ).text() == ""
        widget(window, QPushButton, "review_preview_images_button").click()
        assert "nicht verknüpft" in widget(
            window, QLabel, "review_preview_rgb_integrity",
        ).text()
        window._open_project("P2")
        assert widget(
            window, QLabel, "review_preview_thermal_integrity",
        ).text() == ""
        assert widget(
            window, QLabel, "review_preview_rgb_integrity",
        ).text() == ""
        assert audit_count(window._project_service, "P1") == 0
        assert audit_count(window._project_service, "P2") == 0
    finally:
        window.close()


def set_review_locator_geometry(window, *, thermal_size=(180, 130),
                                rgb_size=(190, 140), rgb_validated=1):
    service = window._project_service
    with service.database.connect() as db:
        db.execute(
            "UPDATE thermal_frames SET width=?, height=? "
            "WHERE project_id='P1' AND frame_id='T1'",
            thermal_size,
        )
        db.execute(
            "UPDATE findings SET pixel_x=90, pixel_y=65 "
            "WHERE project_id='P1' AND finding_id='F1'"
        )
        db.execute(
            "UPDATE image_frames SET width=?, height=? "
            "WHERE project_id='P1' AND frame_id='V1'",
            rgb_size,
        )
        db.execute(
            "UPDATE finding_sensor_links SET rgb_pixel_x=95, rgb_pixel_y=70, "
            "transform_validated=? WHERE project_id='P1' AND finding_id='F1'",
            (rgb_validated,),
        )


def test_qt_local_inspection_shows_validated_pixel_position_hints(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        for name in ("review_preview_thermal_locator", "review_preview_rgb_locator"):
            assert widget(window, QLabel, name).text() == ""
        widget(window, QPushButton, "review_preview_images_button").click()
        for name in ("review_preview_thermal_locator", "review_preview_rgb_locator"):
            text = widget(window, QLabel, name).text()
            assert "Grüne Zielmarke" in text
            assert "keine" in text.lower()
            assert str(folder) not in text
            assert "PRIVATE_CLIENT" not in text
        for name in ("review_preview_thermal", "review_preview_rgb"):
            pixmap = widget(window, QLabel, name).pixmap()
            assert pixmap is not None and not pixmap.isNull()
        assert audit_count(window._project_service, "P1") == 0
        assert window._project_service.import_summary("P1").unreviewed_findings == 2
    finally:
        window.close()


def test_qt_refuses_locator_on_wrong_thermal_frame_dimensions(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window, thermal_size=(640, 512))
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert "stimmen nicht exakt überein" in widget(
            window, QLabel, "review_preview_thermal_locator",
        ).text()
        assert "Grüne Zielmarke" in widget(
            window, QLabel, "review_preview_rgb_locator",
        ).text()
        thermal = widget(window, QLabel, "review_preview_thermal").pixmap()
        assert thermal is not None and not thermal.isNull()
        assert audit_count(window._project_service, "P1") == 0
    finally:
        window.close()


def test_qt_unvalidated_rgb_link_has_no_target_even_with_matching_image(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window, rgb_validated=0)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert "Grüne Zielmarke" in widget(
            window, QLabel, "review_preview_thermal_locator",
        ).text()
        assert "nicht als validiert gespeichert" in widget(
            window, QLabel, "review_preview_rgb_locator",
        ).text()
        assert widget(window, QLabel, "review_preview_rgb").pixmap() is not None
    finally:
        window.close()


def test_qt_locator_status_clears_on_selection_and_project_switch(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        choices = widget(window, QListWidget, "pending_review_findings")
        choices.setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert "Grüne Zielmarke" in widget(
            window, QLabel, "review_preview_thermal_locator",
        ).text()
        choices.setCurrentRow(1)
        for name in ("review_preview_thermal_locator", "review_preview_rgb_locator"):
            assert widget(window, QLabel, name).text() == ""
        widget(window, QPushButton, "review_preview_images_button").click()
        assert "stimmen nicht exakt überein" not in widget(
            window, QLabel, "review_preview_thermal_locator",
        ).text()
        window._open_project("P2")
        for name in ("review_preview_thermal_locator", "review_preview_rgb_locator"):
            assert widget(window, QLabel, name).text() == ""
        assert audit_count(window._project_service, "P1") == 0
        assert audit_count(window._project_service, "P2") == 0
    finally:
        window.close()


def test_qt_shows_native_pixel_detail_beside_overview_without_review(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    service = window._project_service
    set_review_locator_geometry(window)
    original_thermal = (folder / "T.JPG").read_bytes()
    original_rgb = (folder / "V.JPG").read_bytes()
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        items = widget(window, QListWidget, "pending_review_findings")
        items.setCurrentRow(0)
        for name in ("review_preview_thermal_detail", "review_preview_rgb_detail"):
            assert no_pixmap(widget(window, QLabel, name))
        widget(window, QPushButton, "review_preview_images_button").click()
        for name, size in (
            ("review_preview_thermal_detail", (180, 130)),
            ("review_preview_rgb_detail", (190, 140)),
        ):
            pixmap = widget(window, QLabel, name).pixmap()
            assert pixmap is not None and not pixmap.isNull()
            assert (pixmap.width(), pixmap.height()) == size
        assert "maximal 256" in widget(
            window, QLabel, "review_preview_detail_header",
        ).text()
        assert (folder / "T.JPG").read_bytes() == original_thermal
        assert (folder / "V.JPG").read_bytes() == original_rgb
        assert audit_count(service, "P1") == 0
        assert service.import_summary("P1").unreviewed_findings == 2
    finally:
        window.close()


def test_qt_detail_is_absent_for_unvalidated_rgb_or_mismatched_frame(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window, thermal_size=(640, 512), rgb_validated=0)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        for name in ("review_preview_thermal_detail", "review_preview_rgb_detail"):
            label = widget(window, QLabel, name)
            assert no_pixmap(label)
            assert "nicht verfügbar" in label.text()
        assert not no_pixmap(widget(window, QLabel, "review_preview_thermal"))
        assert not no_pixmap(widget(window, QLabel, "review_preview_rgb"))
        assert audit_count(window._project_service, "P1") == 0
    finally:
        window.close()


def test_qt_detail_clears_immediately_on_selection_and_project_switch(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        choices = widget(window, QListWidget, "pending_review_findings")
        choices.setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert not no_pixmap(widget(window, QLabel, "review_preview_thermal_detail"))
        choices.setCurrentRow(1)
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal_detail"))
        assert no_pixmap(widget(window, QLabel, "review_preview_rgb_detail"))
        widget(window, QPushButton, "review_preview_images_button").click()
        assert no_pixmap(widget(window, QLabel, "review_preview_rgb_detail"))
        window._open_project("P2")
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal_detail"))
        assert no_pixmap(widget(window, QLabel, "review_preview_rgb_detail"))
        assert audit_count(window._project_service, "P1") == 0
        assert audit_count(window._project_service, "P2") == 0
    finally:
        window.close()


def test_qt_modified_image_hash_suppresses_original_and_detail(
    qt_app, tmp_path, monkeypatch,
):
    window, folder = seeded_window(tmp_path)
    set_review_locator_geometry(window)
    service = window._project_service
    add_original_sha(service, "P1", "T1", "thermal", (folder / "T.JPG").read_bytes())
    Image.new("RGB", (180, 130), (51, 61, 71)).save(folder / "T.JPG")
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **kw: str(folder),
    )
    try:
        widget(window, QListWidget, "pending_review_findings").setCurrentRow(0)
        widget(window, QPushButton, "review_preview_images_button").click()
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal"))
        assert no_pixmap(widget(window, QLabel, "review_preview_thermal_detail"))
        assert "Abweichende Import-Prüfsumme" in widget(
            window, QLabel, "review_preview_thermal_integrity",
        ).text()
        assert "nicht verfügbar" in widget(
            window, QLabel, "review_preview_thermal_detail",
        ).text()
        assert not no_pixmap(widget(window, QLabel, "review_preview_rgb_detail"))
        assert audit_count(service, "P1") == 0
    finally:
        window.close()
