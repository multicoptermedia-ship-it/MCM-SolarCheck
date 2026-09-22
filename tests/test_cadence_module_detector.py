from mcm_solarcheck.vision.cadence_module_detector import CadenceConfirmedModuleDetector

def test_missing_image_fails_closed(tmp_path):
 assert CadenceConfirmedModuleDetector().detect(tmp_path/'missing.jpg')==()

def test_detector_has_stable_name():
 assert CadenceConfirmedModuleDetector().name=='cadence_confirmed_pv_module_v1'
