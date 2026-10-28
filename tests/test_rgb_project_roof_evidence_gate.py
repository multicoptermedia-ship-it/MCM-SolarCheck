"""Project-bound ENU camera -> independently surveyed rooftop per-camera screen.

Uses only synthetic SQLite, 3 synthetic original file placeholders and 3
synthetic cameras. No user images, no ODM/online services, no DB writes.
"""
from pathlib import Path
import hashlib
import json
import sqlite3

import numpy as np
import pytest

from mcm_solarcheck.services.rgb_project_roof_evidence_gate import (
    screen_project_rgb_roof_geometry,
)
from mcm_solarcheck.services.rgb_project_roof_evidence_cli import main


def _fixture(tmp_path):
    photos=tmp_path/"originals"
    photos.mkdir()
    dbfile=tmp_path/"project.sqlite3"
    names=[]
    with sqlite3.connect(dbfile) as db:
        db.execute("CREATE TABLE projects(project_id TEXT)")
        db.execute("CREATE TABLE image_frames(project_id TEXT, frame_id TEXT, source_file TEXT, width INTEGER, height INTEGER)")
        db.execute("INSERT INTO projects VALUES ('SC-TEST')")
        for i in range(3):
            filename=photos / f"DJI_20260825123000_{120+i:04d}_V.JPG"
            filename.write_bytes(b"synthetic-photo-placeholder")
            fid=f"rgb-{i}"
            names.append(fid)
            db.execute("INSERT INTO image_frames VALUES (?,?,?,?,?)",
                       ("SC-TEST",fid,str(filename),128,128))
    k=np.array([40.,40.,64.,64.])
    centers=np.array([[.2*i,0.,10.] for i in range(3)],dtype=np.float64)
    rotation=np.diag([1.,-1.,-1.])
    rots=np.repeat(rotation[None,:,:],3,axis=0)
    arrays={
        "camera_centers_enu_candidate_m":centers,
        "camera_to_enu_candidate":rots,
        "landmarks_enu_candidate_m":np.zeros((10,3),np.float64),
        "intrinsics_undistorted_pixels":k,
    }
    manifest={
        "schema":"mcm.rgb_camera_enu_candidate.v1",
        "candidate_npz":"rgb-camera-enu-candidate-unverified.npz",
        "camera_frame_ids":names,
        "survey_evidence_authenticity_verified":False,
        "metric_scale_verified":False,
        "georeferencing_verified":False,
        "roof_plane_verified":False,
        "eligible_for_verified_roof_tiles":False,
        "orthophoto_verified":False,
    }
    gcps={
        "schema":"mcm.rgb_independent_enu_controls.v1",
        "fit_controls":[{"control_id":f"gcp-fit-{j}",
                         "point_enu_m":[10.+j,10.+2*j,5.]}
                        for j in range(4)],
        "holdout_controls":[{"control_id":f"gcp-held-{j}",
                             "point_enu_m":[-10.-j,15.+j,8.]}
                            for j in range(4)],
    }
    observations=[]
    for i,fid in enumerate(names):
        for j,(x,y) in enumerate(((-1.,-1.),(-1.,1.),(1.,-1.),(1.,1.))):
            observations.append({
                "frame_id":fid,
                "control_id":f"roof-{i}-{j}",
                "undistorted_pixel_xy":[64.+4.*(x-.2*i),64.-4.*y],
                "surveyed_point_enu_m":[x,y,0.],
                "used_in_3d_gcp_fit":False,
            })
    roof={
        "schema":"mcm.rgb_project_roof_holdouts.v1",
        "project_id":"SC-TEST",
        "calibration_evidence":{
            "undistorted_pixel_coordinates":True,
            "calibration_reference":"independent synthetic calibration record",
            "roof_survey_reference":"synthetic roof control register",
        },
        "plane":{"point_enu_m":[0.,0.,0.],"normal_enu":[0.,0.,1.]},
        "grid":{"u_min_m":-1.,"v_min_m":-1.,"metres_per_pixel":.1,
                "width":20,"height":20,"tile_side_px":16},
        "allowed_rooftop_error_m":.1,
        "controls":observations,
    }
    return dbfile,photos,manifest,arrays,gcps,roof


def _run_fixture(db,manifest,arrays,gcps,roof):
    return screen_project_rgb_roof_geometry(db,"SC-TEST",manifest,arrays,gcps,roof)


def test_all_imported_rgb_cameras_checked_against_independent_roof_plane(tmp_path):
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    before=hashlib.sha256(db.read_bytes()).hexdigest()
    audit=_run_fixture(db,manifest,arrays,gcps,roof)
    assert audit.source_count==3
    assert audit.rooftop_holdout_count==12
    assert audit.largest_per_camera_error_m<1e-10
    assert audit.candidate_tile_count==4
    assert not audit.metric_scale_verified
    assert not audit.survey_authenticity_verified
    assert not audit.eligible_for_verified_roof_tiles
    assert not audit.orthophoto_verified
    assert hashlib.sha256(db.read_bytes()).hexdigest()==before


def test_swapped_project_or_missing_camera_blocks_preflight(tmp_path):
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    roof["project_id"]="SC-OTHER"
    with pytest.raises(ValueError,match="another SolarCheck project"):
        _run_fixture(db,manifest,arrays,gcps,roof)
    roof["project_id"]="SC-TEST"
    manifest["camera_frame_ids"].pop()
    with pytest.raises(ValueError,match="EVERY"):
        _run_fixture(db,manifest,arrays,gcps,roof)


def test_roof_holdout_mismatch_and_missing_frame_block(tmp_path):
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    roof["controls"][0]["undistorted_pixel_xy"][0]+=8
    with pytest.raises(ValueError,match="residual"):
        _run_fixture(db,manifest,arrays,gcps,roof)
    roof["controls"][0]["undistorted_pixel_xy"][0]-=8
    roof["controls"]=[p for p in roof["controls"] if p["frame_id"]!="rgb-2"]
    with pytest.raises(ValueError,match="four|at least"):
        _run_fixture(db,manifest,arrays,gcps,roof)


def test_reused_gcp_control_or_false_review_flag_blocks(tmp_path):
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    roof["controls"][0]["control_id"]=gcps["fit_controls"][0]["control_id"]
    with pytest.raises(ValueError,match="disjoint"):
        _run_fixture(db,manifest,arrays,gcps,roof)
    roof["controls"][0]["control_id"]="roof-0-0"
    manifest["orthophoto_verified"]=True
    with pytest.raises(ValueError,match="verified"):
        _run_fixture(db,manifest,arrays,gcps,roof)


def test_cancel_and_weak_distribution_block(tmp_path):
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    with pytest.raises(RuntimeError,match="cancelled"):
        screen_project_rgb_roof_geometry(
            db,"SC-TEST",manifest,arrays,gcps,roof,should_cancel=lambda:True,
        )
    for p in roof["controls"][:4]:
        p["surveyed_point_enu_m"]=[0.,0.,0.]
    with pytest.raises(ValueError,match="distributed"):
        _run_fixture(db,manifest,arrays,gcps,roof)


def test_local_cli_writes_only_unverified_review_report_and_never_originals(tmp_path,capsys):
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    files=[]
    for name,data in (("rgb-camera-enu-candidate-unverified.json",manifest),
                      ("fit-and-held-gcp.json",gcps),
                      ("roof-heldout.json",roof)):
        p=tmp_path/name
        p.write_text(json.dumps(data),encoding="utf-8")
        files.append(p)
    npz=tmp_path/"rgb-camera-enu-candidate-unverified.npz"
    np.savez_compressed(npz,**arrays)
    folder=tmp_path/"output"
    folder.mkdir()
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (db,*files,npz,*photos.iterdir())}
    assert main([
        "--database",str(db),"--project-id","SC-TEST",
        "--candidate-npz",str(npz),"--candidate-json",str(files[0]),
        "--gcp-survey-json",str(files[1]),
        "--roof-survey-json",str(files[2]),
        "--output-directory",str(folder),
    ])==0
    output=json.loads((folder/"rgb-project-roof-evidence-unverified.json").read_text())
    assert output["imported_rgb_sources_checked"]==3
    assert output["independent_roof_observations_checked"]==12
    assert output["eligible_for_verified_roof_tiles"] is False
    assert output["orthophoto_verified"] is False
    assert output["survey_authenticity_verified"] is False
    assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (db,*files,npz,*photos.iterdir())}==before
    assert "orthophoto_verified" in capsys.readouterr().out


def _write_real_synthetic_primary_jpegs(photos):
    import cv2
    for i,photo in enumerate(sorted(photos.iterdir())):
        image=np.full((128,128,3),90+10*i,dtype=np.uint8)
        assert cv2.imwrite(str(photo),image)


def test_single_cli_full_project_evidence_then_diagnostic_png_and_valid_masks(tmp_path,capsys):
    from mcm_solarcheck.services.rgb_project_roof_diagnostic_vertical import (
        render_unverified_project_roof_tiles,
    )
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    _write_real_synthetic_primary_jpegs(photos)
    roof["calibration_evidence"]["distortion_coefficients"]=[0.,0.,0.,0.,0.]
    roof["calibration_evidence"]["lens_correction_reference"]="synthetic pinned calibration"
    paths=[]
    for name,payload in (
        ("rgb-camera-enu-candidate-unverified.json",manifest),
        ("fit-and-held-gcp.json",gcps),
        ("roof-heldout.json",roof),
    ):
        path=tmp_path/name
        path.write_text(json.dumps(payload),encoding="utf-8")
        paths.append(path)
    npz=tmp_path/"rgb-camera-enu-candidate-unverified.npz"
    np.savez_compressed(npz,**arrays)
    out=tmp_path/"new-output"
    out.mkdir()
    source_files=(db,npz,*paths,*sorted(photos.iterdir()))
    original={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    assert main([
        "--database",str(db),"--project-id","SC-TEST",
        "--candidate-npz",str(npz),
        "--candidate-json",str(paths[0]),
        "--gcp-survey-json",str(paths[1]),
        "--roof-survey-json",str(paths[2]),
        "--output-directory",str(out),
        "--render-diagnostic-tiles",
    ])==0
    metadata=json.loads((out/"rgb-roof-unverified-diagnostic.json").read_text())
    assert metadata["whole_imported_rgb_series_processed"] is True
    assert metadata["rgb_source_count"]==3
    assert metadata["tile_count"]==4
    assert metadata["covered_fraction"]==pytest.approx(1.)
    assert metadata["independent_roof_holdout_count"]==12
    assert metadata["overlap_observations"]>0
    assert metadata["overlap_visual_review_required"] is True
    assert metadata["survey_authenticity_verified"] is False
    assert metadata["metric_scale_verified"] is False
    assert metadata["eligible_for_verified_roof_tiles"] is False
    assert metadata["orthophoto_verified"] is False
    assert metadata["pv_module_detection_performed"] is False
    assert len(list(out.glob("rgb-roof-r*-c*.png")))==8
    assert original=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    assert "orthophoto_verified" in capsys.readouterr().out


def test_bad_holdout_blocks_diagnostic_png_before_photo_read(tmp_path,monkeypatch):
    from mcm_solarcheck.services.rgb_project_roof_diagnostic_vertical import (
        render_unverified_project_roof_tiles,
    )
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    out=tmp_path/"empty-output"
    out.mkdir()
    roof["calibration_evidence"].update({
        "distortion_coefficients":[0.]*5,
        "lens_correction_reference":"external synthetic calibration",
    })
    roof["controls"][0]["undistorted_pixel_xy"][0]+=8.
    import cv2
    def no_decode(*args,**kwargs):
        raise AssertionError("preflight must precede decoding")
    monkeypatch.setattr(cv2,"imread",no_decode)
    with pytest.raises(ValueError,match="residual"):
        render_unverified_project_roof_tiles(
            db,"SC-TEST",manifest,arrays,gcps,roof,out,
        )
    assert not list(out.iterdir())


def test_whole_flight_cancellation_cleans_all_diagnostic_files(tmp_path):
    from mcm_solarcheck.services.rgb_project_roof_diagnostic_vertical import (
        RGBDiagnosticRoofCancelled,render_unverified_project_roof_tiles,
    )
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    _write_real_synthetic_primary_jpegs(photos)
    roof["calibration_evidence"].update({
        "distortion_coefficients":[0.]*5,
        "lens_correction_reference":"external synthetic calibration",
    })
    out=tmp_path/"new-output"
    out.mkdir()
    abort={"now":False}
    with pytest.raises(RGBDiagnosticRoofCancelled):
        render_unverified_project_roof_tiles(
            db,"SC-TEST",manifest,arrays,gcps,roof,out,
            should_cancel=lambda:abort["now"],
            on_progress=lambda n,total:abort.update(now=True),
        )
    assert not list(out.iterdir())


def test_unverified_candidate_cannot_bypass_verified_pixel_renderer(tmp_path):
    from mcm_solarcheck.services.module_plane_rectification import (
        rectify_module_surface, sample_unverified_surface_candidate,
        ModuleSurfaceGrid,
    )
    from mcm_solarcheck.services.module_plane_projection import (
        PinholeIntrinsics, CameraExtrinsicsENU, SurveyedPlane3D,
    )
    from mcm_solarcheck.domain.models import ImageFrame, Pose
    from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
    k=PinholeIntrinsics(40.,40.,64.,64.)
    extrinsics=CameraExtrinsicsENU(
        (0.,0.,10.), ((1.,0.,0.),(0.,-1.,0.),(0.,0.,-1.)),
    )
    plane=SurveyedPlane3D((0.,0.,0.),(0.,0.,1.))
    grid=ModuleSurfaceGrid(-1.,-1.,.1,20,20)
    image=np.full((128,128,3),100,dtype=np.uint8)
    frame=ImageFrame("rgb-0",tmp_path/"dummy.jpg",width=128,height=128,
                     camera_pose=Pose(0.,-90.,0.))
    candidate=VerifiedCameraGeometry(k,extrinsics,128,128,
                                     "unverified","unverified","unverified",
                                     False,False)
    with pytest.raises(ValueError,match="lens correction"):
        rectify_module_surface(frame,image,candidate,plane,grid)
    diagnostic=sample_unverified_surface_candidate(
        image,k,extrinsics,plane,grid,
    )
    assert int(diagnostic.valid_mask.sum())==400
    assert not diagnostic.georeferencing_verified


def test_rejected_diagnostic_output_directory_does_not_change_photos(tmp_path):
    from mcm_solarcheck.services.rgb_project_roof_diagnostic_vertical import (
        render_unverified_project_roof_tiles,
    )
    db,photos,manifest,arrays,gcps,roof=_fixture(tmp_path)
    _write_real_synthetic_primary_jpegs(photos)
    roof["calibration_evidence"].update({
        "distortion_coefficients":[0.]*5,
        "lens_correction_reference":"external synthetic calibration",
    })
    with pytest.raises(ValueError,match="overlap"):
        render_unverified_project_roof_tiles(
            db,"SC-TEST",manifest,arrays,gcps,roof,photos,
        )
