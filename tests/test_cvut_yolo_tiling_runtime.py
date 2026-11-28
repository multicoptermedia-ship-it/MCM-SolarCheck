"""Real standard COCO evaluator with generated masks, no downloaded imagery."""
import pytest
pytest.importorskip('pycocotools')

from mcm_solarcheck.services.cvut_yolo_tiled_comparison import score_coco
from mcm_solarcheck.vision.detection import ModuleDetection


def fixture(count=1):
    image=dict(id=1,width=256,height=256)
    categories=[dict(id=1,name='pv_panel')]
    # Integer corner coordinates describe a20x10-pixel mask.
    annotations=[dict(id=i+1,image_id=1,category_id=1,iscrowd=0,
        segmentation=[[10+i*2,10,30+i*2,10,30+i*2,20,10+i*2,20]],
        area=200,bbox=[10+i*2,10,20,10]) for i in range(count)]
    exact=ModuleDetection(((9.5,9.5),(29.5,9.5),(29.5,19.5),(9.5,19.5)),.9)
    return image,categories,annotations,exact


def test_empty_detection_counts_are_positive_despite_integer_ignore_arrays():
    image,categories,annotations,_=fixture()
    scores=score_coco(image,categories,annotations,())
    assert all(s['reference_instances']==s['missed_references']==1
        and s['matched_instances']==s['additional_predictions']==0 for s in scores.values())


def test_native_pixel_centers_are_converted_back_to_coco_corner_coordinates():
    image,categories,annotations,exact=fixture()
    assert all(s['matched_instances']==1 and s['additional_predictions']==s['missed_references']==0
        and s['AP']>.99 for s in score_coco(image,categories,annotations,(exact,)).values())


def test_half_module_is_not_counted_as_a_complete_boundary_at_strict_iou():
    image,categories,annotations,_=fixture()
    half=ModuleDetection(((9.5,9.5),(21.5,9.5),(21.5,19.5),(9.5,19.5)),.99)
    scores=score_coco(image,categories,annotations,(half,))
    assert scores['iou050']['matched_instances']==1
    assert scores['iou075']['matched_instances']==0
    assert scores['iou075']['additional_predictions']==scores['iou075']['missed_references']==1


def test_large_park_evaluation_does_not_silently_stop_after_one_hundred_detections():
    image,categories,annotations,_=fixture()
    unmatched=ModuleDetection(((99.5,99.5),(119.5,99.5),(119.5,109.5),(99.5,109.5)),.8)
    assert score_coco(image,categories,annotations,(unmatched,)*120)['iou050']['additional_predictions']==120


def test_evaluation_budget_fails_instead_of_publishing_truncated_counts():
    image,categories,annotations,exact=fixture()
    with pytest.raises(ValueError,match='Bounded'):
        score_coco(image,categories,annotations,(exact,)*5001)
