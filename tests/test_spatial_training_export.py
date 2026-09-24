import json
import pytest
from types import SimpleNamespace
from mcm_solarcheck.review.training_export import build_spatial_training_index


def snapshot(box=(1,2,20,30), polygon=None):
    manifest={"samples":[{"sample_id":"s","source_frame_id":"T1","source_file":"t.jpg","modality":"thermal","content_sha256":"abc"}],
      "labels":[{"label_id":1,"source_frame_id":"T1","module_id":"M1","finding_id":None,"inspection_group_id":"flight-1","defect_class":"thermal_hotspot_candidate"}],
      "geometries":[{"label_id":1,"source_frame_id":"T1","reviewer":"alice","representation":"rendered_rgb","box_xyxy":box,"polygon_px":polygon}]}
    return SimpleNamespace(manifest_json=json.dumps(manifest))


def test_detection_export_carries_reviewed_box_and_representation():
    row=build_spatial_training_index(snapshot(),"detection")[0]
    assert row["box_xyxy"]==[1,2,20,30]
    assert row["representation"]=="rendered_rgb"
    assert row["split"] in {"train","validation","test"}


def test_detection_export_fails_without_reviewed_box():
    with pytest.raises(ValueError,match="bounding box"):
        build_spatial_training_index(snapshot(box=None,polygon=[[1,1],[2,1],[1,2]]),"detection")


def test_segmentation_export_fails_without_reviewed_polygon():
    with pytest.raises(ValueError,match="polygon"):
        build_spatial_training_index(snapshot(),"segmentation")
