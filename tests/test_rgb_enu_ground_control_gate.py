"""Separate fitting-vs-held-out ENU GCP gates, synthetic survey only."""
from dataclasses import replace
import numpy as np
import pytest

from mcm_solarcheck.services.rgb_enu_ground_control_gate import (
    RGBSurveyed3DControl,fit_enu_candidate_from_survey,
)


def _survey():
    rng=np.random.default_rng(20261028)
    pts=np.column_stack((rng.uniform(-3,3,24),rng.uniform(-2,2,24),
                         rng.normal(0,.08,24)))
    # Synthetic 15-degree proper ENU rotation + arbitrary translation and scale.
    angle=np.deg2rad(15)
    rotation=np.array([[np.cos(angle),-np.sin(angle),0],
                       [np.sin(angle),np.cos(angle),0],[0,0,1.]])
    scale=2.75
    shift=np.array((441.0,511.5,34.2))
    enu=scale*(pts@rotation.T)+shift
    pose=tuple(np.column_stack((
        np.eye(3),np.array((-.3*i,.01*i, -1.5))
    )) for i in range(5))
    def controls(indices):
        return tuple(RGBSurveyed3DControl(
            f"independent-control-{i}",int(i),tuple(float(x) for x in enu[i]),
        ) for i in indices)
    return pose,pts,controls(range(8)),controls(range(8,16)),enu,rotation,scale,shift


def _fit(pose,pts,train,held,**kw):
    return fit_enu_candidate_from_survey(
        pose,pts,train,held,
        fit_survey_provenance="synthetic external fit register",
        holdout_survey_provenance="synthetic external held-out register",
        allowed_max_error_m=.05,**kw,
    )


def test_true_similarity_keeps_all_cameras_and_holdouts_separate():
    pose,pts,fit,held,enu,rotation,scale,shift=_survey()
    before=pts.copy()
    result=_fit(pose,pts,fit,held)
    assert result.fit_control_count==8 and result.held_out_control_count==8
    assert result.scale_m_per_arbitrary_unit==pytest.approx(scale,rel=1e-10)
    np.testing.assert_allclose(result.rotation_to_enu,rotation,atol=1e-11)
    np.testing.assert_allclose(result.origin_enu_m,shift,atol=1e-9)
    np.testing.assert_allclose(result.landmark_points_enu_candidate_m,enu,atol=1e-9)
    assert result.fit_max_error_m<1e-9 and result.holdout_max_error_m<1e-9
    assert len(result.camera_extrinsics_candidate)==5
    for camera,original in zip(result.camera_extrinsics_candidate,pose):
        old_center=-original[:,:3].T@original[:,3]
        expected=scale*rotation@old_center+shift
        np.testing.assert_allclose(camera.center_enu_m,expected,atol=1e-9)
        np.testing.assert_allclose(camera.camera_to_enu,rotation@original[:,:3].T,atol=1e-12)
    np.testing.assert_array_equal(pts,before)
    assert not result.metric_scale_verified
    assert not result.independent_survey_authenticity_verified
    assert not result.georeferencing_verified
    assert not result.orthophoto_verified


def test_corrupted_separate_holdout_rejected_without_relaxing_tolerance():
    pose,pts,train,hold,*_=_survey()
    bad=list(hold)
    p=bad[2]
    bad[2]=replace(p,point_enu_m=(p.point_enu_m[0]+.20,
                                 p.point_enu_m[1],p.point_enu_m[2]))
    with pytest.raises(ValueError,match="residual"):
        _fit(pose,pts,train,tuple(bad))


def test_training_and_holdout_landmarks_must_never_overlap():
    pose,pts,train,hold,*_=_survey()
    bad=(replace(hold[0],landmark_index=train[0].landmark_index),)+hold[1:]
    with pytest.raises(ValueError,match="independent"):
        _fit(pose,pts,train,bad)
    with pytest.raises(ValueError,match="duplicate"):
        _fit(pose,pts,train,hold+(hold[0],))


def test_collinear_reference_points_cannot_establish_3d_orientation():
    pose,pts,train,hold,*_=_survey()
    line=tuple(replace(c,point_enu_m=(float(i),0.,0.))
               for i,c in enumerate(train))
    with pytest.raises(ValueError,match="collinear|distributed"):
        _fit(pose,pts,line,hold)


def test_reflection_is_not_a_valid_proper_enu_orientation():
    pose,pts,train,hold,enu,*_=_survey()
    mirror=enu.copy()
    mirror[:,2]*=-1
    mirror_fit=tuple(replace(c,point_enu_m=tuple(mirror[c.landmark_index]))
                     for c in train)
    mirror_held=tuple(replace(c,point_enu_m=tuple(mirror[c.landmark_index]))
                      for c in hold)
    with pytest.raises(ValueError,match="residual"):
        _fit(pose,pts,mirror_fit,mirror_held)


def test_unprovided_provenance_and_cancel_fail_closed():
    pose,pts,train,hold,*_=_survey()
    with pytest.raises(ValueError,match="provenance"):
        fit_enu_candidate_from_survey(
            pose,pts,train,hold,fit_survey_provenance="",
            holdout_survey_provenance="ok",allowed_max_error_m=.05,
        )
    with pytest.raises(RuntimeError,match="cancelled"):
        _fit(pose,pts,train,hold,should_cancel=lambda:True)
