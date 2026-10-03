import cv2,numpy as np
from mcm_solarcheck.vision.opencv_module_detector import OpenCVModuleDetector

def test_detects_separated_blue_modules(tmp_path):
    im=np.full((600,800,3),230,np.uint8)
    cv2.rectangle(im,(100,100),(180,150),(120,70,40),-1)
    cv2.rectangle(im,(400,300),(480,350),(120,70,40),-1)
    p=tmp_path/"rgb.jpg";cv2.imwrite(str(p),im)
    d=OpenCVModuleDetector(max_dimension=800).detect(p)
    assert len(d)==2
    assert all(x.class_name=="pv_module" for x in d)

def test_rejects_large_dark_roof_region(tmp_path):
    im=np.full((600,800,3),230,np.uint8);cv2.rectangle(im,(20,20),(780,580),(120,70,40),-1)
    p=tmp_path/"rgb.jpg";cv2.imwrite(str(p),im)
    assert OpenCVModuleDetector(max_dimension=800).detect(p)==()

def test_missing_image_fails_closed(tmp_path):
    assert OpenCVModuleDetector().detect(tmp_path/"missing.jpg")==()
