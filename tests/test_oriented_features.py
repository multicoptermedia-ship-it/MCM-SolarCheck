from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.oriented_features import OrientedStructuralPoint,oriented_intersections


def line(x1,y1,x2,y2,angle):
    return StructuralLine(x1,y1,x2,y2,((x2-x1)**2+(y2-y1)**2)**.5,angle)


def test_intersection_preserves_crossing_angle():
    lines=(line(10,50,90,50,0),line(50,10,50,90,90))
    points=oriented_intersections(lines,100,100)
    assert len(points)==1
    assert abs(points[0].x-50)<1e-9;assert abs(points[0].y-50)<1e-9
    assert points[0].crossing_angle_deg==90


def test_rotation_does_not_change_crossing_angle():
    a=OrientedStructuralPoint(1,2,10,80);b=OrientedStructuralPoint(3,4,47,117)
    assert a.crossing_angle_deg==b.crossing_angle_deg==70


def test_near_parallel_lines_are_rejected():
    lines=(line(0,0,100,10,5),line(0,20,100,40,11))
    assert oriented_intersections(lines,100,100,minimum_angle_deg=25)==()


def test_duplicate_location_keeps_more_distinct_crossing():
    lines=(line(0,50,100,50,0),line(50,0,50,100,90),line(0,20,100,80,31))
    points=oriented_intersections(lines,100,100,dedup_distance_px=2)
    center=min(points,key=lambda p:(p.x-50)**2+(p.y-50)**2)
    assert center.crossing_angle_deg==90


def test_infinite_line_crossing_far_beyond_segments_is_rejected():
    lines=(line(10,20,30,20,0),line(80,60,80,90,90))
    assert oriented_intersections(lines,100,100,segment_extension_fraction=.2)==()


def test_small_broken_edge_gap_can_be_bridged():
    lines=(line(10,50,45,50,0),line(50,10,50,45,90))
    points=oriented_intersections(lines,100,100,segment_extension_fraction=.2)
    assert len(points)==1
    assert abs(points[0].x-50)<1e-9;assert abs(points[0].y-50)<1e-9


def test_zero_extension_rejects_crossing_beyond_endpoint():
    lines=(line(10,50,45,50,0),line(50,10,50,45,90))
    assert oriented_intersections(lines,100,100,segment_extension_fraction=0)==()


def test_negative_extension_fails():
    try:oriented_intersections((),100,100,segment_extension_fraction=-.1)
    except ValueError as exc:assert 'extension' in str(exc)
    else:raise AssertionError('expected ValueError')


def test_invalid_dimensions_fail():
    try:oriented_intersections((),0,100)
    except ValueError as exc:assert 'dimensions' in str(exc)
    else:raise AssertionError('expected ValueError')
