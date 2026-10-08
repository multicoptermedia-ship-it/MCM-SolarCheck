from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest
from mcm_solarcheck.domain.models import ImageFrame,Pose
from mcm_solarcheck.pairing.geometry import capture_geometry_delta,unavailable_transform,PixelTransform

def test_realistic_capture_delta_is_measured_not_assumed():
    t=datetime(2025,8,25,10,13,58,296180,tzinfo=timezone.utc)
    thermal=ImageFrame('T-0001',Path('T.JPG'),timestamp_utc=t,camera_pose=Pose(yaw_deg=23.8,pitch_deg=-89.9),flight_pose=Pose(yaw_deg=23.4))
    rgb=ImageFrame('V-0001',Path('V.JPG'),timestamp_utc=t+timedelta(seconds=.10102),camera_pose=Pose(yaw_deg=23.8,pitch_deg=-89.9),flight_pose=Pose(yaw_deg=23.3))
    delta=capture_geometry_delta(rgb,thermal)
    assert delta.time_delta_s==pytest.approx(.10102);assert delta.gimbal_yaw_delta_deg==0;assert delta.flight_yaw_delta_deg==pytest.approx(.1)

def test_unvalidated_transform_refuses_pixel_mapping():
    transform=unavailable_transform()
    assert transform.validated is False
    with pytest.raises(RuntimeError):transform.map_point(320,256)

def test_validated_homography_maps_point():
    transform=PixelTransform('homography',True,640,512,4000,3000,((2,0,10),(0,3,20),(0,0,1)),.8)
    assert transform.map_point(5,7)==(20,41)
