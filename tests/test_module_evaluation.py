from mcm_solarcheck.vision.module_evaluation import ModuleFrameEvaluation,ModuleDevelopmentEvaluation
def test_evaluation_summarizes_without_accuracy_metric():
 q=ModuleDevelopmentEvaluation((ModuleFrameEvaluation("a",4,3,3,"confirmed"),ModuleFrameEvaluation("b",4,0,0,"no_image_support")))
 assert q.processed==2 and q.confirmed_total==3 and q.failure_frames==("b",)
