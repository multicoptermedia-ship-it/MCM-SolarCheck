from mcm_solarcheck.pairing.structural_features import StructuralLine
from mcm_solarcheck.pairing.grid_lines import GridLine,GridLineFamily
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.grid_cell_support import filter_cells_by_finite_support

def test_requires_all_four_finite_sides():
 a=GridLineFamily(0,(GridLine(0,10,1,20),GridLine(0,30,1,20)))
 b=GridLineFamily(90,(GridLine(90,-10,1,20),GridLine(90,-30,1,20)))
 cell=ModuleDetection(((10,10),(10,30),(30,30),(30,10)),.8)
 lines=(StructuralLine(10,10,30,10,20,0),StructuralLine(10,30,30,30,20,0),StructuralLine(10,10,10,30,20,90),StructuralLine(30,10,30,30,20,90))
 assert filter_cells_by_finite_support((cell,),(a,b),lines,tolerance_px=1)==(cell,)
 assert filter_cells_by_finite_support((cell,),(a,b),lines[:-1],tolerance_px=1)==()

def test_rejects_extrapolated_short_boundary():
 a=GridLineFamily(0,(GridLine(0,10,1,20),GridLine(0,30,1,20)));b=GridLineFamily(90,(GridLine(90,-10,1,20),GridLine(90,-30,1,20)))
 cell=ModuleDetection(((10,10),(10,30),(30,30),(30,10)),.8)
 lines=(StructuralLine(10,10,20,10,10,0),StructuralLine(10,30,30,30,20,0),StructuralLine(10,10,10,30,20,90),StructuralLine(30,10,30,30,20,90))
 assert filter_cells_by_finite_support((cell,),(a,b),lines,tolerance_px=1)==()


def test_accepts_collinear_fragmented_side_support():
 a=GridLineFamily(0,(GridLine(0,10,1,20),GridLine(0,30,1,20)));b=GridLineFamily(90,(GridLine(90,-10,1,20),GridLine(90,-30,1,20)))
 cell=ModuleDetection(((10,10),(10,30),(30,30),(30,10)),.8)
 lines=(StructuralLine(10,10,20,10,10,0),StructuralLine(20,10,30,10,10,0),StructuralLine(10,30,30,30,20,0),StructuralLine(10,10,10,30,20,90),StructuralLine(30,10,30,30,20,90))
 assert filter_cells_by_finite_support((cell,),(a,b),lines,tolerance_px=1)==(cell,)


def test_rejects_parallel_fragments_that_do_not_share_expected_side_line():
 a=GridLineFamily(0,(GridLine(0,10,1,20),GridLine(0,30,1,20)));b=GridLineFamily(90,(GridLine(90,-10,1,20),GridLine(90,-30,1,20)))
 cell=ModuleDetection(((10,10),(10,30),(30,30),(30,10)),.8)
 lines=(StructuralLine(10,10,20,10,10,0),StructuralLine(20,12,30,12,10,0),StructuralLine(10,30,30,30,20,0),StructuralLine(10,10,10,30,20,90),StructuralLine(30,10,30,30,20,90))
 assert filter_cells_by_finite_support((cell,),(a,b),lines,tolerance_px=1)==()
