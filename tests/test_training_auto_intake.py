from pathlib import Path
from types import SimpleNamespace

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class _Grade:
    value="ok"


def _quality():
    stats=SimpleNamespace(minimum=1,maximum=2,mean=1.5,median=1.5,p95=2,p99=2)
    return SimpleNamespace(statistics=stats,grade=_Grade())


def test_imported_thermal_frame_is_automatically_indexed(tmp_path):
    image=tmp_path/"thermal.jpg"; image.write_bytes(b"thermal")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    frame=ThermalFrame(frame_id="T1",source_file=image,thermal_width=2,thermal_height=2)
    db.save_thermal_frame("P",frame,_quality())
    rows=db.training_samples("P")
    assert [(r["source_frame_id"],r["modality"]) for r in rows] == [("T1","thermal")]


def test_imported_rgb_frames_are_automatically_indexed(tmp_path):
    image=tmp_path/"rgb.jpg"; image.write_bytes(b"rgb")
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","Project")
    db.save_image_frames("P",[ImageFrame(frame_id="R1",source_file=image)])
    rows=db.training_samples("P")
    assert [(r["source_frame_id"],r["modality"]) for r in rows] == [("R1","rgb")]
