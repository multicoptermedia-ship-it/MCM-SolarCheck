"""Window-close regression: do not destroy a running integrity worker."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.services.deployment import DeploymentMode


class FakeWorker:
    def __init__(self):
        self.cancel_requests = 0

    def request_cancel(self):
        self.cancel_requests += 1


def test_close_is_deferred_while_integrity_scan_active():
    app = QApplication.instance() or QApplication([])
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP)
    worker = FakeWorker()
    window._integrity_thread = object()
    window._integrity_worker = worker
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()
    assert window._integrity_close_pending
    assert worker.cancel_requests == 1
    window._integrity_thread = None
    window._integrity_worker = None
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
