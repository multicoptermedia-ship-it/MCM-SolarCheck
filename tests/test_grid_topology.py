from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint
from mcm_solarcheck.pairing.grid_topology import grid_topology_signatures,topology_distance


def grid(w,h,rotation=0):
    return tuple(OrientedStructuralPoint(x*w,y*h,rotation,(rotation+90)%180) for y in (.2,.5,.8) for x in (.15,.4,.7,.9))


def test_topology_is_resolution_independent_for_same_grid():
    thermal=grid(640,512);rgb=grid(4000,3000)
    ts=grid_topology_signatures(thermal,(640,512));rs=grid_topology_signatures(rgb,(4000,3000))
    assert len(ts)==len(rs)
    assert max(topology_distance(a,b) for a,b in zip(ts,rs))<1e-3


def test_corner_and_interior_have_different_occupancy():
    sig=grid_topology_signatures(grid(640,512),(640,512))
    corner=sig[0];interior=sig[5]
    assert corner.occupancy!=interior.occupancy
    assert topology_distance(corner,interior)==float('inf')


def test_axis_order_is_canonicalized():
    points=grid(640,512);swapped=tuple(OrientedStructuralPoint(p.x,p.y,p.angle_b_deg,p.angle_a_deg) for p in points)
    a=grid_topology_signatures(points,(640,512));b=grid_topology_signatures(swapped,(640,512))
    assert all(topology_distance(x,y)<1e-9 for x,y in zip(a,b))


def test_invalid_size_is_rejected():
    try:grid_topology_signatures((),(0,512))
    except ValueError as exc:assert 'dimensions' in str(exc)
    else:raise AssertionError('expected ValueError')
