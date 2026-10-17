import json
import pytest
from mcm_solarcheck.services.orthophoto_survey_job import load_surveyed_orthophoto_job

def test_job_requires_verified_surface(tmp_path):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"rgb": {}, "thermal": {}, "planar_surface_verified": False}))
    with pytest.raises(ValueError, match="verified"):
        load_surveyed_orthophoto_job(p)

def test_job_requires_explicit_layers(tmp_path):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"rgb": {}, "thermal": {}, "planar_surface_verified": True}))
    with pytest.raises(ValueError, match="controls"):
        load_surveyed_orthophoto_job(p)
