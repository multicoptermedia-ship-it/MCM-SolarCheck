from mcm_solarcheck.vision.polygon_geometry import convex_polygon_iou,is_valid_module_polygon
def test_polygon_iou_exact_and_disjoint():
 a=((0,0),(10,0),(10,10),(0,10))
 assert abs(convex_polygon_iou(a,a)-1)<1e-6
 assert convex_polygon_iou(a,((20,0),(30,0),(30,10),(20,10)))==0
def test_self_intersecting_module_polygon_rejected():
 assert not is_valid_module_polygon(((0,0),(10,10),(0,10),(10,0)))
 assert is_valid_module_polygon(((0,0),(10,0),(10,10),(0,10)))
