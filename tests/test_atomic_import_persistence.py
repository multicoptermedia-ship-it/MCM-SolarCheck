from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _result(name):
    return SimpleNamespace(
        frame=SimpleNamespace(frame_id=name),
        quality=object(),
        findings=(),
    )


class _AtomicDatabase(ProjectDatabase):
    def __init__(self):
        self.events = []

    @contextmanager
    def connect(self):
        self.events.append("begin")
        try:
            yield object()
        except Exception:
            self.events.append("rollback")
            raise
        else:
            self.events.append("commit")

    def _save_thermal_frame(self, db, project_id, frame, quality):
        self.events.append(("frame", frame.frame_id))

    def _save_training_frame(self, db, project_id, frame, modality):
        self.events.append(("training", frame.frame_id))

    def _save_findings(self, db, project_id, findings):
        self.events.append(("findings", project_id))

    def _save_sensor_links(self, db, project_id, findings):
        self.events.append(("links", project_id))


def test_atomic_thermal_batch_uses_one_transaction():
    database = _AtomicDatabase()

    database.save_thermal_results("project-a", (_result("a"), _result("b")))

    assert database.events.count("begin") == 1
    assert database.events.count("commit") == 1
    assert ("frame", "a") in database.events
    assert ("frame", "b") in database.events


def test_atomic_thermal_batch_rolls_back_on_write_failure():
    database = _AtomicDatabase()
    original = database._save_thermal_frame

    def fail_second(db, project_id, frame, quality):
        original(db, project_id, frame, quality)
        if frame.frame_id == "b":
            raise RuntimeError("write failed")

    database._save_thermal_frame = fail_second
    with pytest.raises(RuntimeError, match="write failed"):
        database.save_thermal_results("project-a", (_result("a"), _result("b")))

    assert database.events.count("begin") == 1
    assert database.events.count("rollback") == 1
    assert "commit" not in database.events


def test_atomic_thermal_batch_rolls_back_on_heartbeat_failure():
    database = _AtomicDatabase()
    calls = 0

    def heartbeat():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("lease expired")

    with pytest.raises(RuntimeError, match="lease expired"):
        database.save_thermal_results(
            "project-a",
            (_result("a"), _result("b")),
            heartbeat=heartbeat,
        )

    assert calls == 2
    assert database.events.count("rollback") == 1
    assert ("frame", "a") in database.events
    assert ("frame", "b") not in database.events


def _project_import():
    rgb = SimpleNamespace(frame_id="rgb-a", source_file="rgb.jpg", timestamp_utc=None, camera_make=None, camera_model=None, width=None, height=None, position=None, metadata={})
    thermal = _result("thermal-a")
    pair = SimpleNamespace(pair_id="pair-a", rgb_frame_id="rgb-a", thermal_frame_id="thermal-a", confidence=1.0, method="test", distance_m=None, time_delta_s=None)
    return SimpleNamespace(rgb_frames=(rgb,), thermal_batch=SimpleNamespace(results=(thermal,), failures=()), pairs=(pair,))


def test_complete_project_import_shares_one_transaction():
    database = _AtomicDatabase()
    database.save_project_import("project-a", _project_import())
    assert database.events.count("begin") == 1
    assert database.events.count("commit") == 1
    assert ("frame", "thermal-a") in database.events
