"""End-to-end saved windowed BA -> independent ENU controls -> candidate only."""
import json
import numpy as np
import pytest

from mcm_solarcheck.services.rgb_enu_candidate_cli import main


def _files(tmp_path):
    rng=np.random.default_rng(802)
    xyz=np.column_stack((rng.uniform(-3,3,22),rng.uniform(-2,2,22),
                         rng.normal(0,.12,22)))
    rotation=np.eye(3)
    scale=3.5
    offset=np.array([325.,172.,21.])
    measured=scale*(xyz@rotation.T)+offset
    cam=np.stack([np.column_stack((np.eye(3),np.array((-.2*i,0.,-1.))))
                  for i in range(5)])
    source=tmp_path/"rgb-global-windowed-ba-unscaled.npz"
    np.savez_compressed(
        source,
        poses_world_to_camera_arbitrary=cam,
        landmarks_xyz_arbitrary=xyz,
        observation_landmark_indices=np.tile(np.arange(22,dtype=np.int32),5),
        observation_frame_indices=np.repeat(np.arange(5,dtype=np.int32),22),
        observation_pixels_xy=np.zeros((5*22,2),dtype=np.float64),
        calibrated_intrinsics=np.array([700.,700.,400.,300.]),
    )
    metadata=tmp_path/"rgb-global-windowed-ba-unscaled.json"
    metadata.write_text(json.dumps({
        "schema":"mcm.rgb_global_windowed_ba.v1",
        "result_npz":source.name,
        "source_3d_geometry_not_metric":True,
        "metric_scale_verified":False,
        "georeferencing_verified":False,
        "orthophoto_verified":False,
        "global_joint_ba_completed":False,
        "camera_frame_ids":[f"camera-{i}" for i in range(5)],
    }),encoding="utf-8")
    def controls(ids):
        return [
            {"control_id":f"survey-{i}","landmark_index":i,
             "point_enu_m":[float(x) for x in measured[i]]}
            for i in ids
        ]
    controls_data={
        "schema":"mcm.rgb_independent_enu_controls.v1",
        "fit_survey_provenance":"synthetic independent fit survey",
        "holdout_survey_provenance":"synthetic holdout register",
        "allowed_max_error_m":.03,
        "minimum_spread_m":.5,
        "fit_controls":controls(range(8)),
        "holdout_controls":controls(range(8,16)),
    }
    survey=tmp_path/"independent-survey.json"
    survey.write_text(json.dumps(controls_data),encoding="utf-8")
    output=tmp_path/"new-enu-output"
    output.mkdir()
    return source,metadata,survey,output,controls_data,measured


def _run(source,metadata,survey,output):
    return main([
        "--ba-npz",str(source),"--ba-json",str(metadata),
        "--survey-json",str(survey),"--output-directory",str(output),
    ])


def test_saved_full_camera_network_is_fit_only_to_training_gcp_and_reports_holdout(tmp_path,capsys):
    source,metadata,survey,out,_,measured=_files(tmp_path)
    before=(source.read_bytes(),survey.read_bytes())
    assert _run(source,metadata,survey,out)==0
    assert (source.read_bytes(),survey.read_bytes())==before
    summary=json.loads((out/"rgb-camera-enu-candidate-unverified.json").read_text(encoding="utf-8"))
    assert summary["fit_control_count"]==8
    assert summary["holdout_control_count"]==8
    assert summary["holdout_max_residual_m"]<1.e-9
    assert not summary["metric_scale_verified"]
    assert not summary["survey_evidence_authenticity_verified"]
    assert not summary["eligible_for_verified_roof_tiles"]
    assert not summary["orthophoto_verified"]
    with np.load(out/summary["candidate_npz"],allow_pickle=False) as data:
        np.testing.assert_allclose(data["landmarks_enu_candidate_m"],measured,atol=1e-9)
        assert data["camera_to_enu_candidate"].shape==(5,3,3)
        assert data["camera_centers_enu_candidate_m"].shape==(5,3)
    assert "orthophoto_verified" in capsys.readouterr().out


def test_holdout_gcp_error_blocks_every_output_file(tmp_path):
    source,metadata,survey,out,payload,_=_files(tmp_path)
    payload["holdout_controls"][0]["point_enu_m"][0]+=1.0
    survey.write_text(json.dumps(payload),encoding="utf-8")
    with pytest.raises(ValueError,match="residual"):
        _run(source,metadata,survey,out)
    assert not list(out.iterdir())


def test_input_claiming_verified_geo_or_missing_fit_not_accepted(tmp_path):
    source,metadata,survey,out,payload,_=_files(tmp_path)
    meta=json.loads(metadata.read_text(encoding="utf-8"))
    meta["metric_scale_verified"]=True
    metadata.write_text(json.dumps(meta),encoding="utf-8")
    with pytest.raises(ValueError,match="unscaled"):
        _run(source,metadata,survey,out)
    assert not list(out.iterdir())
    meta["metric_scale_verified"]=False
    metadata.write_text(json.dumps(meta),encoding="utf-8")
    payload["fit_controls"]=payload["fit_controls"][:3]
    survey.write_text(json.dumps(payload),encoding="utf-8")
    with pytest.raises(ValueError,match="four"):
        _run(source,metadata,survey,out)
    assert not list(out.iterdir())
