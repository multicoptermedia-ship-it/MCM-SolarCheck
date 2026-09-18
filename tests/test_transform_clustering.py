from types import SimpleNamespace
from mcm_solarcheck.pairing.transform_clustering import cluster_grid_transforms,transform_distance_px

def est(tx=0.,ty=0.,scale=1.):
    transform=SimpleNamespace(matrix=((scale,0.,tx),(0.,scale,ty),(0.,0.,1.)))
    return SimpleNamespace(estimate=SimpleNamespace(transform=transform))

def test_near_duplicate_transforms_cluster():
    a,b=est(),est(.5,.5)
    got=cluster_grid_transforms((a,b),640,512,maximum_projection_difference_px=1)
    assert len(got)==1 and len(got[0].members)==2

def test_physical_grid_shift_remains_separate():
    a,b=est(),est(25,0)
    got=cluster_grid_transforms((a,b),640,512,maximum_projection_difference_px=3)
    assert len(got)==2

def test_scale_difference_is_measured_across_image_not_only_origin():
    a,b=est(),est(scale=1.01)
    assert transform_distance_px(a,b,640,512)>6
    assert len(cluster_grid_transforms((a,b),640,512,maximum_projection_difference_px=3))==2

def test_complete_link_prevents_chaining():
    a,b,c=est(0),est(2),est(4)
    got=cluster_grid_transforms((a,b,c),640,512,maximum_projection_difference_px=3)
    assert [len(x.members) for x in got]==[2,1]

def test_invalid_dimensions_fail_closed():
    import pytest
    with pytest.raises(ValueError):cluster_grid_transforms((),0,512)
