"""Explicit Qt action -> fake external tool -> paired SQLite intake -> reopen."""
import os
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSlider
import pytest

from mcm_solarcheck.gui import micmac_dialog as gui
from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.services import micmac_orthophotos as mm
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute

from test_micmac_orthophotos import scene, fake_micmac, no_network


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def local_settings(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    monkeypatch.setattr(gui, 'QSettings', lambda *args: settings)
    return settings


def wait_for(app, predicate):
    deadline = time.monotonic() + 10
    while not predicate():
        app.processEvents()
        if time.monotonic() >= deadline:
            pytest.fail('owned MicMac worker did not reach expected state')
        time.sleep(.01)
    app.processEvents()


def close_window(app, window):
    window.close()
    wait_for(app, lambda: window._micmac_dialog is None or not window._micmac_dialog.running)


def start_dialog(window, exe, output):
    window._open_micmac_dialog('P1')
    dialog = window._micmac_dialog
    dialog.executable.setText(str(exe))
    dialog.output.setText(str(output))
    dialog.start_button.click()
    return dialog


def test_explicit_gui_job_registers_only_completed_pair_and_reopens(scene, monkeypatch, app, local_settings):
    service, exe, output, _ = scene
    calls = fake_micmac(monkeypatch)
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    before = service.state('P1')
    try:
        window._open_project('P1')
        window._workflow_navigation.button(ShellRoute.PROCESSING).click()
        page = window._pages[ShellRoute.PROCESSING]
        page.findChild(QPushButton, 'processing_generate_micmac').click()
        assert window._micmac_dialog is not None
        assert calls == []  # No automatic run when opening the project/dialog.
        dialog = window._micmac_dialog
        dialog.executable.setText(str(exe))
        dialog.output.setText(str(output))
        dialog.start_button.click()
        wait_for(app, lambda: window._micmac_dialog is None)
        assert len(calls) == 12
        pairs = service.project_orthophoto_pairs('P1')
        assert len(pairs) == 1 and pairs[0]['source_kind'] == 'micmac'
        assert pairs[0]['thermal_value_kind'] == 'visual'
        assert pairs[0]['inspection_status'] == 'metadata_only'
        assert service.state('P1') == before
        assert window.current_route is ShellRoute.PLANT_OVERVIEW
        assert window._pages[ShellRoute.PLANT_OVERVIEW].findChild(QSlider, 'orthophoto_thermal_opacity_slider') is not None
        assert local_settings.value('micmac/executable') == str(exe)
    finally:
        close_window(app, window)
    reopened = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    try:
        reopened._open_project('P1')
        assert reopened._pages[ShellRoute.PLANT_OVERVIEW].findChild(QSlider, 'orthophoto_thermal_opacity_slider') is not None
        assert len(calls) == 12
    finally:
        close_window(app, reopened)


def test_tool_failure_keeps_dialog_open_and_does_not_register_partial_pair(scene, monkeypatch, app):
    service, exe, output, _ = scene
    fake_micmac(monkeypatch, fail_layer='thermal')
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    try:
        window._open_project('P1')
        dialog = start_dialog(window, exe, output)
        wait_for(app, lambda: not dialog.running)
        assert 'Tapas' in dialog.status.text()
        assert dialog.start_button.isEnabled()
        assert service.project_orthophoto_pairs('P1') == ()
        dialog.reject()
        assert window._micmac_dialog is None
    finally:
        close_window(app, window)


@pytest.mark.parametrize('action', ('close_window', 'switch_project'))
def test_close_and_project_switch_cancel_owned_job_without_publishing(scene, monkeypatch, app, action):
    service, exe, output, _ = scene
    entered = []
    def wait_for_cancel(executable, args, cwd, log, should_cancel):
        entered.append(True)
        while not should_cancel():
            time.sleep(.01)
        raise mm.MicMacCancelled()
    monkeypatch.setattr(mm, '_execute', wait_for_cancel)
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    try:
        window._open_project('P1')
        window.show()
        start_dialog(window, exe, output)
        wait_for(app, lambda: bool(entered))
        if action == 'close_window':
            window.close()
        else:
            window._open_project('P2')
        wait_for(app, lambda: window._micmac_dialog is None)
        if action == 'close_window':
            assert not window.isVisible()
        else:
            assert window._current_project_id == 'P2'
        assert service.project_orthophoto_pairs('P1') == ()
        assert service.project_orthophoto_pairs('P2') == ()
    finally:
        close_window(app, window)


def test_stale_results_and_changed_gnss_cannot_register_in_current_project(scene, monkeypatch, app):
    service, exe, output, _ = scene
    fake_micmac(monkeypatch)
    result = mm.generate_micmac_orthophotos(service.database, 'P1', exe, output)
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    try:
        window._open_project('P2')
        window._receive_micmac_pair('P1', result)
        assert service.project_orthophoto_pairs('P1') == service.project_orthophoto_pairs('P2') == ()
        window._open_project('P1')
        with service.database.connect() as db:
            db.execute('UPDATE image_frames SET altitude_m=altitude_m+1 WHERE project_id=?', ('P1',))
        window._receive_micmac_pair('P1', result)
        assert service.project_orthophoto_pairs('P1') == ()
        assert 'Projekteingaben geändert' in window._micmac_status
    finally:
        close_window(app, window)


def test_online_shell_cannot_start_local_micmac(scene, app):
    service, _, _, _ = scene
    window = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        window._current_project_id = 'P1'
        window._open_micmac_dialog('P1')
        assert window._micmac_dialog is None
        assert not window._pages[ShellRoute.PROCESSING].findChild(QPushButton, 'processing_generate_micmac').isEnabled()
    finally:
        close_window(app, window)
