"""Integration with the existing offline SQLite database."""
from mcm_solarcheck.offline.composition import build_offline_services
from shared_ui.offline_projects import offline_project_list


def test_offline_projects_use_existing_database(tmp_path):
    db_path = tmp_path / "projects.sqlite3"
    services = build_offline_services(db_path)
    services.projects.create_project("roof-1", "Anlage West")
    assert offline_project_list(db_path) == [{"id": "roof-1", "name": "Anlage West"}]
