"""Synthetic desktop-job checks without private flight imagery."""
import json
import pytest
from mcm_solarcheck.services.orthophoto_survey_job import load_surveyed_orthophoto_job


def _job():
    points = [[0, 0], [7, 0], [7, 7], [0, 7]]
    def layer(name):
        return {
            "controls": [{"frame_id": name, "pixel_points": points, "world_points": points, "independently_surveyed": True}],
            "reference": {"crs": "EPSG:25832", "transform": [1, 0, 0, 0, 1, 0], "width": 8, "height": 8},
            "destination": name + ".tif",
        }
    return {"rgb": layer("rgb"), "thermal": layer("thermal"), "planar_surface_verified": True}


def test_valid_job_resolves_destinations(tmp_path):
    path = tmp_path / "job.json"
    path.write_text(json.dumps(_job()), encoding="utf-8")
    args = load_surveyed_orthophoto_job(path)
    assert args[4] == tmp_path / "rgb.tif"
    assert args[5] == tmp_path / "thermal.tif"


@pytest.mark.parametrize("bad", ["nan", "few", "duplicate"])
def test_invalid_controls_rejected(tmp_path, bad):
    job = _job()
    if bad == "nan":
        job["rgb"]["controls"][0]["pixel_points"][0][0] = float("nan")
    elif bad == "few":
        job["rgb"]["controls"][0]["pixel_points"].pop()
    else:
        job["rgb"]["controls"].append(dict(job["rgb"]["controls"][0]))
    path = tmp_path / "job.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ValueError):
        load_surveyed_orthophoto_job(path)
