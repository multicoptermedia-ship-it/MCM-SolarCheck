from math import sqrt
import pytest
from mcm_solarcheck.domain.models import PVModule
from mcm_solarcheck.vision.module_observations import module_observations

def test_modules_convert_to_identity_observations():
 m=PVModule("f:M-0001","f",((10,20),(110,20),(110,220),(10,220)),.9,"x")
 o=module_observations((m,))[0]
 assert o.frame_id=="f" and o.local_id=="f:M-0001" and o.center==pytest.approx((60,120)) and o.width==pytest.approx(100) and o.height==pytest.approx(200)

def test_dimensions_are_rotation_invariant():
 s=sqrt(2)/2
 def rot(x,y):return (60+(x-60)*s-(y-120)*s,120+(x-60)*s+(y-120)*s)
 m=PVModule("f:M-0001","f",tuple(rot(x,y) for x,y in ((10,20),(110,20),(110,220),(10,220))))
 o=module_observations((m,))[0]
 assert o.center==pytest.approx((60,120));assert o.width==pytest.approx(100);assert o.height==pytest.approx(200)

def test_degenerate_polygon_is_rejected():
 m=PVModule("f:M-0001","f",((0,0),(1,0),(2,0)))
 with pytest.raises(ValueError,match="positive area"):module_observations((m,))
