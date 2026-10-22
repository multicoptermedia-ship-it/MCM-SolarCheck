"""Identity readiness is evidence, never automatically verified module geometry.

Synthetic, independent test projects only. No private images or GIS coordinates.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QTableWidget

from mcm_solarcheck.services.shell_navigation import ShellRoute
from mcm_solarcheck.offline.entrypoint import build_offline_window
from test_plant_overview_service import seeded_service
from test_gui_plant_overview_vertical import sample_window


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_project_wide_candidate_totals_do_not_infer_physical_module_count(tmp_path):
    service = seeded_service(tmp_path)
    p1 = service.plant_overview("P1", limit=1, offset=1)
    counts = p1.identity_readiness
    assert counts.observed_modules == 2
    assert counts.linked_observations == 1
    assert counts.unresolved_observations == 1
    assert counts.distinct_candidate_labels == 1
    assert counts.orphaned_identity_links == 0
    assert len(p1.modules) == 1
    # Candidate numbers are always project-scoped.
    p2 = service.plant_overview("P2").identity_readiness
    assert (p2.observed_modules, p2.linked_observations,
            p2.unresolved_observations, p2.distinct_candidate_labels) == (1, 0, 1, 0)


def test_identity_readiness_detects_orphan_links_without_modifying_them(tmp_path):
    service = seeded_service(tmp_path)
    with service.database.connect() as sql:
        sql.execute(
            "INSERT INTO module_identity_links "
            "(project_id, frame_id, local_module_id, physical_module_id, status) "
            "VALUES ('P1','V','NO-MODULE','M-ORPHAN','matched')"
        )
    before = service.database.path.read_bytes()
    for _ in range(2):
        readiness = service.plant_overview("P1").identity_readiness
        assert readiness.orphaned_identity_links == 1
        assert readiness.distinct_candidate_labels == 1
        assert readiness.linked_observations == 1
    assert service.database.path.read_bytes() == before


def test_gui_explains_candidate_ids_and_real_image_frame_counts(qt_app, tmp_path):
    window = sample_window(tmp_path)
    try:
        window._open_project("P1")
        window.show_route(ShellRoute.PLANT_OVERVIEW)
        page = window._pages[ShellRoute.PLANT_OVERVIEW]
        label = page.findChild(QLabel, "plant_identity_readiness")
        assert label is not None
        assert "1 von 2 Modulbeobachtungen" in label.text()
        assert "1 ohne belastbaren Vorschlag" in label.text()
        assert "keine geprüfte Modulanzahl" in label.text()
        images = page.findChild(QLabel, "plant_image_evidence_summary")
        assert images is not None
        assert "1 Thermal" in images.text()
        assert "0 Analysepaare" in images.text()
        assert page.findChild(QTableWidget, "plant_modules_table").rowCount() == 2

        window._open_project("P2")
        other = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert "0 von 1 Modulbeobachtungen" in other.findChild(
            QLabel, "plant_identity_readiness"
        ).text()
        assert other.findChild(QLabel, "plant_identity_data_warning") is None
    finally:
        window.close()


def test_gui_warns_about_orphaned_identity_link(qt_app, tmp_path):
    window = sample_window(tmp_path)
    try:
        with window._project_service.database.connect() as sql:
            sql.execute(
                "INSERT INTO module_identity_links "
                "(project_id, frame_id, local_module_id, physical_module_id, status) "
                "VALUES ('P1','T1','MISSING','M-9999','new')"
            )
        window._open_project("P1")
        window.show_route(ShellRoute.PLANT_OVERVIEW)
        warning = window._pages[ShellRoute.PLANT_OVERVIEW].findChild(
            QLabel, "plant_identity_data_warning"
        )
        assert warning is not None
        assert "1 gespeicherte ID-Verweise" in warning.text()
        assert "prüfen" in warning.text()
    finally:
        window.close()


def test_many_modules_keep_project_wide_readiness_across_pages(qt_app, tmp_path):
    window = sample_window(tmp_path, module_count=105)
    try:
        window._open_project("P1")
        window.show_route(ShellRoute.PLANT_OVERVIEW)
        first = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert "1 von 105 Modulbeobachtungen" in first.findChild(
            QLabel, "plant_identity_readiness"
        ).text()
        first.findChild(
            __import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton,
            "plant_next_page"
        ).click()
        second = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert "1 von 105 Modulbeobachtungen" in second.findChild(
            QLabel, "plant_identity_readiness"
        ).text()
        assert second.findChild(QTableWidget, "plant_modules_table").rowCount() == 5
    finally:
        window.close()


def test_no_modules_never_creates_synthetic_site_map(qt_app, tmp_path):
    window = build_offline_window(tmp_path / "no-modules.sqlite3")
    try:
        window._project_service.create_project("ONLY-FRAMES", "Import pilot")
        window._open_project("ONLY-FRAMES")
        window.show_route(ShellRoute.PLANT_OVERVIEW)
        page = window._pages[ShellRoute.PLANT_OVERVIEW]
        assert page.findChild(QLabel, "plant_no_module_geometry") is not None
        assert "0 von 0" in page.findChild(QLabel, "plant_identity_readiness").text()
        assert page.findChild(QTableWidget, "plant_modules_table").rowCount() == 0
        assert "keine pixelgenaue Sensorregistrierung" in page.findChild(
            QLabel, "plant_image_evidence_summary"
        ).text()
    finally:
        window.close()
