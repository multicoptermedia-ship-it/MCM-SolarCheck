import pytest
from mcm_solarcheck.review.yolo_export import yolo_detection_line, build_yolo_detection_manifest, write_yolo_detection_dataset


def test_yolo_detection_line_normalizes_reviewed_box():
    assert yolo_detection_line("hotspot",{"hotspot":2},(100,50,300,150),400,200)=="2 0.5000000000 0.5000000000 0.5000000000 0.5000000000"


def test_yolo_detection_line_rejects_unknown_class():
    with pytest.raises(ValueError,match="no YOLO class id"):
        yolo_detection_line("unknown",{"hotspot":0},(1,1,2,2),10,10)


def test_yolo_detection_line_rejects_out_of_bounds_box():
    with pytest.raises(ValueError,match="outside source image bounds"):
        yolo_detection_line("hotspot",{"hotspot":0},(0,0,11,10),10,10)

import json
from types import SimpleNamespace


def _snapshot(source_file="t.jpg", content_sha256="abc"):
    manifest={"samples":[{"sample_id":"thermal:abc","source_frame_id":"T1","source_file":str(source_file),"modality":"thermal","content_sha256":content_sha256}],
      "labels":[{"label_id":1,"source_frame_id":"T1","module_id":"M1","finding_id":None,"inspection_group_id":"flight-1","defect_class":"hotspot"}],
      "geometries":[{"label_id":1,"source_frame_id":"T1","reviewer":"alice","representation":"rendered_rgb","box_xyxy":[100,50,300,150],"polygon_px":None}]}
    return SimpleNamespace(manifest_json=json.dumps(manifest))


def test_yolo_manifest_is_deterministic_and_preserves_provenance(tmp_path):
    from hashlib import sha256
    source=tmp_path/"t.jpg"
    source.write_bytes(b"thermal")
    digest=sha256(b"thermal").hexdigest()
    snapshot=_snapshot(source,digest)
    a=build_yolo_detection_manifest(snapshot,{"hotspot":0},{"thermal:abc":(400,200)})
    b=build_yolo_detection_manifest(snapshot,{"hotspot":0},{"thermal:abc":(400,200)})
    assert a==b
    row=a["rows"][0]
    assert row["content_sha256"]==digest
    assert row["representation"]=="rendered_rgb"
    write_yolo_detection_dataset(a,tmp_path/"yolo")
    assert (tmp_path/"yolo"/"manifest.json").is_file()
    assert (tmp_path/"yolo"/"labels"/"thermal_abc.txt").read_text().startswith("0 0.5000000000")


def test_yolo_manifest_requires_exact_source_dimensions():
    with pytest.raises(ValueError,match="missing source dimensions"):
        build_yolo_detection_manifest(_snapshot(),{"hotspot":0},{})
