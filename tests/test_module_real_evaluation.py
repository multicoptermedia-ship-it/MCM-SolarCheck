from pathlib import Path
from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_real_evaluation import evaluate_detector_pair
def d(x):return ModuleDetection(((x,0),(x+100,0),(x+100,200),(x,200)),.8)
class F:
 def __init__(self,x):self.x=x
 def detect(self,p):return self.x
def test_pair_evaluation_preserves_evidence_counts():
 frame=ImageFrame("f",Path("x"),width=1000,height=1000)
 q=evaluate_detector_pair((frame,),F((d(0),d(300))),F((d(10),)))
 assert q.frames[0].grid_candidates==2 and q.frames[0].confirmed==1
