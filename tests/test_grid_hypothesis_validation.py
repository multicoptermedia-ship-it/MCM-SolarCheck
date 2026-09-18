from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.pairing.grid_line_selection import CrossResolutionGridSelection
from mcm_solarcheck.pairing.grid_hypothesis_validation import validate_grid_hypotheses,select_unique_grid_hypothesis,PhysicalAnchor,filter_grid_hypotheses_by_anchors

def family(angle,offsets):
    return GridLineFamily(angle,tuple(GridLine(angle,float(x),1,100.0) for x in offsets))

def selection(ta,to,ra,ro):
    t=family(ta,to);r=family(ra,ro)
    return CrossResolutionGridSelection(t,r,1,1,len(to),0.0,False)

def test_clean_two_axis_hypothesis_passes_independent_holdout():
    a=selection(0,(0,10,20,30),0,(0,60,120,180))
    b=selection(90,(0,10,20,30),90,(0,60,120,180))
    result=validate_grid_hypotheses((a,),(b,))
    assert len(result)==1
    assert result[0].estimate.quality.validated
    assert result[0].estimate.fit_points>=6

def test_wrong_line_identity_fails_holdout_instead_of_being_forced():
    a=selection(0,(0,10,20,30,40),0,(0,60,120,180,240))
    # Non-projectively inconsistent RGB offsets model a wrong phase/line identity.
    b=selection(90,(0,10,20,30,40),90,(0,60,125,195,280))
    result=validate_grid_hypotheses((a,),(b,),maximum_rms_error_px=2,maximum_error_px=5)
    assert result==()

def test_insufficient_grid_evidence_fails_closed():
    a=selection(0,(0,10,20),0,(0,60,120))
    b=selection(90,(0,10,20),90,(0,60,120))
    assert validate_grid_hypotheses((a,),(b,))==()


def test_repetitive_equal_quality_hypotheses_fail_uniqueness():
    a=selection(0,(0,10,20,30),0,(0,60,120,180))
    b=selection(90,(0,10,20,30),90,(0,60,120,180))
    one=validate_grid_hypotheses((a,),(b,))[0]
    assert select_unique_grid_hypothesis((one,one)) is None

def test_single_validated_hypothesis_is_unique():
    a=selection(0,(0,10,20,30),0,(0,60,120,180))
    b=selection(90,(0,10,20,30),90,(0,60,120,180))
    one=validate_grid_hypotheses((a,),(b,))[0]
    assert select_unique_grid_hypothesis((one,)) is one

def test_uniqueness_configuration_is_validated():
    import pytest
    with pytest.raises(ValueError):select_unique_grid_hypothesis((),minimum_control_point_advantage=0)
    with pytest.raises(ValueError):select_unique_grid_hypothesis((),minimum_rms_ratio=1)


def test_independent_physical_anchors_accept_correct_grid_transform():
    a=selection(0,(0,10,20,30),0,(0,60,120,180))
    b=selection(90,(0,10,20,30),90,(0,60,120,180))
    estimate=validate_grid_hypotheses((a,),(b,))[0]
    anchors=(PhysicalAnchor(5,7,30,42),PhysicalAnchor(25,13,150,78))
    assert filter_grid_hypotheses_by_anchors((estimate,),anchors)==(estimate,)

def test_independent_physical_anchors_reject_wrong_identity():
    a=selection(0,(0,10,20,30),0,(0,60,120,180))
    b=selection(90,(0,10,20,30),90,(0,60,120,180))
    estimate=validate_grid_hypotheses((a,),(b,))[0]
    anchors=(PhysicalAnchor(5,7,130,42),PhysicalAnchor(25,13,250,78))
    assert filter_grid_hypotheses_by_anchors((estimate,),anchors)==()

def test_anchor_validation_requires_independent_evidence():
    assert filter_grid_hypotheses_by_anchors((),(PhysicalAnchor(0,0,0,0),),minimum_anchors=2)==()
