from pathlib import Path
from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_batch import detect_modules_batch
class D:
 name="fixture"
 def detect(self,p):
  return (ModuleDetection(((10,10),(110,10),(110,210),(10,210)),.9),)
def test_batch_reports_frame_and_module_totals():
 frames=(ImageFrame("a",Path("a"),width=1000,height=1000),ImageFrame("b",Path("b"),width=1000,height=1000))
 q=detect_modules_batch(frames,D())
 assert q.detected_frames==2 and q.module_count==2
