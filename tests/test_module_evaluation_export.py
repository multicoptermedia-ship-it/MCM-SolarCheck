from mcm_solarcheck.vision.module_evaluation import ModuleFrameEvaluation,ModuleDevelopmentEvaluation
from mcm_solarcheck.vision.module_evaluation_export import evaluation_rows,evaluation_summary
def test_export_is_deterministic_and_auditable():
 e=ModuleDevelopmentEvaluation((ModuleFrameEvaluation("001",4,3,2,"confirmed"),))
 assert evaluation_rows(e)==(("001",4,3,2,"confirmed"),)
 assert evaluation_summary(e)=={"processed":1,"confirmed_total":2,"failure_frames":0}
