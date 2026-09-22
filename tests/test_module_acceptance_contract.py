from mcm_solarcheck.vision.module_acceptance import assess_development_run
from mcm_solarcheck.vision.module_evaluation import ModuleDevelopmentEvaluation,ModuleFrameEvaluation

def ev(*frames):return ModuleDevelopmentEvaluation(tuple(frames))
def f(i='f',g=2,v=2,c=1,s='confirmed'):return ModuleFrameEvaluation(i,g,v,c,s)

def test_acceptance_is_execution_quality_not_accuracy_claim():
 assert assess_development_run(ev(f()),minimum_processed=1).accepted

def test_duplicate_frame_identity_fails_closed():
 assert assess_development_run(ev(f('x'),f('x'))).reason=='invalid_frame_identity'

def test_impossible_confirmed_count_fails_closed():
 assert assess_development_run(ev(f(g=1,v=2,c=2))).reason=='inconsistent_counts'

def test_invalid_threshold_fails_closed():
 assert assess_development_run(ev(f()),minimum_processed=0).reason=='invalid_minimum_processed'
