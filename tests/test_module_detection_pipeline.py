from pathlib import Path
from mcm_solarcheck.domain.models import ImageFrame
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.module_detection_pipeline import detect_modules_in_frame

class Detector:
    name="fixture"
    def detect(self,path):
        assert path==Path("rgb.jpg")
        return (
          ModuleDetection(((100,100),(300,100),(300,500),(100,500)),.95),
          ModuleDetection(((105,105),(305,105),(305,505),(105,505)),.70),
          ModuleDetection(((-5,0),(20,0),(20,30)),.99),
        )

def test_pipeline_runs_detector_and_applies_quality_gate():
    frame=ImageFrame("V-1",Path("rgb.jpg"),width=4000,height=3000)
    run=detect_modules_in_frame(frame,Detector())
    assert run.status=="detected"
    assert len(run.modules)==1
    assert run.modules[0].detector=="fixture"

def test_pipeline_fails_closed_without_image_geometry():
    frame=ImageFrame("V-1",Path("rgb.jpg"))
    run=detect_modules_in_frame(frame,Detector())
    assert run.status=="missing_image_geometry"
    assert run.modules==()

class Empty:
    name="empty"
    def detect(self,path): return ()

def test_pipeline_reports_no_modules():
    frame=ImageFrame("V-1",Path("rgb.jpg"),width=4000,height=3000)
    assert detect_modules_in_frame(frame,Empty()).status=="no_modules"
