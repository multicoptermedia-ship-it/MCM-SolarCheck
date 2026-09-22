from mcm_solarcheck.domain.models import PVModule
from mcm_solarcheck.vision.module_observations import module_observations
def test_modules_convert_to_identity_observations():
 m=PVModule("f:M-0001","f",((10,20),(110,20),(110,220),(10,220)),.9,"x")
 o=module_observations((m,))[0]
 assert o.frame_id=="f" and o.local_id=="f:M-0001" and o.center==(60,120) and o.width==100 and o.height==200
