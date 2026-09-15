import cv2
import numpy as np
from mcm_solarcheck.pairing.structural_features import StructuralLine,detect_structural_lines,structural_intersections


def test_detects_long_rectangle_structure():
    image=np.zeros((512,640,3),dtype=np.uint8)
    cv2.rectangle(image,(100,100),(500,400),(255,255,255),4)
    lines=detect_structural_lines(image,min_length_fraction=.15)
    assert len(lines)>=4
    assert max(line.length for line in lines)>250


def test_intersections_recover_rectangle_corners():
    lines=(StructuralLine(100,100,500,100,400,0),StructuralLine(100,400,500,400,400,0),StructuralLine(100,100,100,400,300,90),StructuralLine(500,100,500,400,300,90))
    points=structural_intersections(lines,640,512)
    coords={(round(p.x),round(p.y)) for p in points}
    assert {(100,100),(500,100),(100,400),(500,400)}<=coords


def test_parallel_lines_do_not_create_intersections():
    lines=(StructuralLine(0,10,100,10,100,0),StructuralLine(0,20,100,20,100,0))
    assert structural_intersections(lines,200,100)==()
