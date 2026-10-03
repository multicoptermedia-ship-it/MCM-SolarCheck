from mcm_solarcheck.vision.module_evaluation import ModuleFrameEvaluation,ModuleDevelopmentEvaluation
from mcm_solarcheck.vision.module_acceptance import assess_development_run
def e(*rows):return ModuleDevelopmentEvaluation(tuple(ModuleFrameEvaluation(*r) for r in rows))
def test_acceptance_requires_real_confirmed_output():
 assert not assess_development_run(e()).accepted
 assert not assess_development_run(e(("a",3,0,0,"no_image_support"))).accepted
 assert assess_development_run(e(("a",3,2,2,"confirmed"))).accepted
def test_strict_acceptance_rejects_failed_frames():
 q=e(("a",3,2,2,"confirmed"),("b",3,0,0,"no_image_support"))
 assert not assess_development_run(q,require_all_confirmed=True).accepted
