from mcm_solarcheck.pairing.registration import ControlPoint,assess_registration,project_homography

def test_exact_homography_is_accepted():
    h=(6.0,0,10,0,5.0,20,0,0,1)
    pts=tuple(ControlPoint(x,y,6*x+10,5*y+20) for x,y in ((0,0),(100,0),(0,100),(100,100),(320,256),(500,400)))
    q=assess_registration(h,pts)
    assert q.validated;assert q.rms_error_px==0;assert q.max_error_px==0

def test_registration_requires_enough_control_points():
    h=(1,0,0,0,1,0,0,0,1)
    pts=tuple(ControlPoint(i,i,i,i) for i in range(4))
    q=assess_registration(h,pts)
    assert not q.validated;assert q.reason=='insufficient_control_points'

def test_bad_reprojection_is_rejected():
    h=(1,0,0,0,1,0,0,0,1)
    pts=tuple(ControlPoint(i*10,i*5,i*10+50,i*5+50) for i in range(6))
    q=assess_registration(h,pts)
    assert not q.validated;assert q.reason=='reprojection_error_too_high'

def test_projective_mapping_divides_by_homogeneous_coordinate():
    assert project_homography((1,0,0,0,1,0,0.01,0,1),100,50)==(50.0,25.0)
