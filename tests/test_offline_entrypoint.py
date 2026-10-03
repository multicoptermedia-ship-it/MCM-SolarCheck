from __future__ import annotations

import ast
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from mcm_solarcheck.offline.entrypoint import build_offline_window
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute


def test_offline_entrypoint_composes_persisted_project_service(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    window = build_offline_window(tmp_path / "offline.sqlite3")

    assert application is not None
    assert window.current_route is ShellRoute.PROJECT
    assert window._deployment is DeploymentMode.OFFLINE_DESKTOP
    assert window._project_service is not None

    project = window._project_service.create_project("P-OFFLINE", "Offline Solarpark")
    assert project.project_id == "P-OFFLINE"
    assert window._project_service.projects()[0].project_id == "P-OFFLINE"


def test_offline_entrypoint_does_not_import_online_product_modules() -> None:
    source = Path("src/mcm_solarcheck/offline/entrypoint.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    assert not any(
        name.startswith("mcm_solarcheck.online") or "online_" in name
        for name in imports
    )


def test_root_app_is_only_offline_compatibility_entrypoint() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]

    assert classes == []
    assert functions == []
    assert "mcm_solarcheck.offline.entrypoint" in source
