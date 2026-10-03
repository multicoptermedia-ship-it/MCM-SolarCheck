from __future__ import annotations

import ast
from pathlib import Path

from mcm_solarcheck.offline.composition import OfflineServices, build_offline_services
from mcm_solarcheck.online.composition import OnlineServices, build_online_services


def test_online_composition_has_stable_product_import_boundary() -> None:
    assert OnlineServices is not None
    assert callable(build_online_services)


def test_offline_composition_builds_shared_project_core(tmp_path) -> None:
    services = build_offline_services(tmp_path / "offline.sqlite")

    assert isinstance(services, OfflineServices)
    project = services.projects.create_project("project-1", "Offline Project")
    assert project.project_id == "project-1"


def test_offline_composition_source_has_no_online_dependency() -> None:
    source_path = (
        Path(__file__).parents[1]
        / "src"
        / "mcm_solarcheck"
        / "offline"
        / "composition.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    assert not any(
        module == "mcm_solarcheck.online"
        or module.startswith("mcm_solarcheck.online.")
        or "online_" in module
        for module in imports
    )
