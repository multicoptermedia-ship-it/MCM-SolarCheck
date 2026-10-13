"""Project adapter contract against existing ProjectRecord attribute names."""
from types import SimpleNamespace

from shared_ui.project_adapter import list_project_summaries


def test_project_list_normalizes_persisted_records():
    reader = SimpleNamespace(projects=lambda: (
        SimpleNamespace(project_id="a", name="Dach A"),
        SimpleNamespace(project_id="b", name="Dach B"),
    ))
    assert list_project_summaries(reader) == [
        {"id": "a", "name": "Dach A"},
        {"id": "b", "name": "Dach B"},
    ]


def test_empty_project_list():
    assert list_project_summaries(SimpleNamespace(projects=lambda: ())) == []
