"""Project-scoped source loading for native orthophoto generation."""
import pytest

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame
from mcm_solarcheck.services.orthophoto_project_sources import project_imported_frames
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_project_source_reader_returns_only_own_imported_frames(tmp_path):
    db = ProjectDatabase(tmp_path / "projects.sqlite")
    db.initialize()
    db.create_project("a", "A")
    db.create_project("b", "B")
    rgb = ImageFrame("rgb-a", tmp_path / "a.png", width=8, height=8)
    thermal = ThermalFrame("thermal-a", tmp_path / "thermal.png", width=8, height=8)
    db.save_image_frames("a", (rgb,))
    from mcm_solarcheck.services.orthophoto_project_sources import project_imported_frames
    rgb_rows, thermal_rows = project_imported_frames(db, "a")
    assert len(rgb_rows) == 1
    assert rgb_rows[0].source_file == rgb.source_file
    assert thermal_rows == ()
    assert project_imported_frames(db, "b") == ((), ())
    with pytest.raises(KeyError, match="Unknown project"):
        project_imported_frames(db, "missing")
