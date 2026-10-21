"""Offline platform startup must work without Python network calls or real data."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")

from mcm_solarcheck.offline.windows_smoke import run_smoke


def test_offline_desktop_works_with_python_connections_blocked():
    run_smoke(headless=True)
