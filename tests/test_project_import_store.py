from types import SimpleNamespace

import pytest

from mcm_solarcheck.storage.import_store import store_project_import


class RecordingDatabase:
    def __init__(self) -> None:
        self.saved = []

    def save_thermal_result(self, project_id, frame, quality, findings) -> None:
        self.saved.append((project_id, frame, quality, findings))


def imported_result():
    first = SimpleNamespace(
        frame="frame-1",
        quality="quality-1",
        findings=("finding-1", "finding-2"),
    )
    second = SimpleNamespace(
        frame="frame-2",
        quality="quality-2",
        findings=(),
    )
    return SimpleNamespace(
        thermal_batch=SimpleNamespace(
            results=(first, second),
            failures=(object(),),
        )
    )


def test_store_project_import_persists_thermal_results_for_project() -> None:
    database = RecordingDatabase()

    summary = store_project_import(database, "user-1", " P-1 ", imported_result())

    assert database.saved == [
        ("P-1", "frame-1", "quality-1", ("finding-1", "finding-2")),
        ("P-1", "frame-2", "quality-2", ()),
    ]
    assert summary.frames_saved == 2
    assert summary.findings_saved == 2
    assert summary.import_failures == 1


@pytest.mark.parametrize(
    ("customer_id", "project_id"),
    [("", "P-1"), ("user-1", " "), (" ", "")],
)
def test_store_project_import_rejects_missing_identity(customer_id, project_id) -> None:
    database = RecordingDatabase()

    with pytest.raises(ValueError):
        store_project_import(database, customer_id, project_id, imported_result())

    assert database.saved == []


def test_store_project_import_heartbeats_after_each_saved_frame() -> None:
    database = RecordingDatabase()
    heartbeats = []

    summary = store_project_import(
        database,
        "user-1",
        "P-1",
        imported_result(),
        heartbeat=lambda: heartbeats.append(len(database.saved)),
    )

    assert summary.frames_saved == 2
    assert heartbeats == [1, 2]


def test_store_project_import_propagates_heartbeat_failure() -> None:
    database = RecordingDatabase()

    def fail_heartbeat():
        raise PermissionError("compute job worker lease expired")

    with pytest.raises(PermissionError, match="lease expired"):
        store_project_import(
            database,
            "user-1",
            "P-1",
            imported_result(),
            heartbeat=fail_heartbeat,
        )

    assert len(database.saved) == 1
