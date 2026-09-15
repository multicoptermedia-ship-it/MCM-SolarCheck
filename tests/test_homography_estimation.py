from mcm_solarcheck.pairing.registration import ControlPoint,estimate_homography


def cp(x,y,rx=None,ry=None):return ControlPoint(x,y,5*x+100 if rx is None else rx,5*y+50 if ry is None else ry)


def fit_points():
    return (cp(10,10),cp(100,10),cp(200,20),cp(20,100),cp(150,120),cp(300,200),cp(500,300),cp(600,450))


def validation_points():return (cp(50,50),cp(250,80),cp(80,300),cp(400,400))


def test_estimates_and_validates_transform_on_independent_points():
    result=estimate_homography(fit_points(),validation_points())
    assert result.quality.validated is True;assert result.transform.validated is True;assert result.inliers>=6
    x,y=result.transform.map_point(100,100);assert abs(x-600)<1e-5;assert abs(y-550)<1e-5


def test_bad_holdout_refuses_otherwise_good_fit():
    bad=(cp(50,50,900,900),cp(250,80,100,100),cp(80,300,3000,100),cp(400,400,100,2500))
    result=estimate_homography(fit_points(),bad)
    assert result.quality.validated is False;assert result.quality.reason=='reprojection_error_too_high';assert result.transform.validated is False


def test_too_few_fit_points_never_estimates_valid_transform():
    result=estimate_homography(fit_points()[:4],validation_points())
    assert result.transform.validated is False;assert result.quality.reason=='insufficient_fit_points';assert result.inliers==0


def test_too_few_holdout_points_never_validates():
    result=estimate_homography(fit_points(),validation_points()[:2])
    assert result.transform.validated is False;assert result.quality.reason=='insufficient_control_points'
