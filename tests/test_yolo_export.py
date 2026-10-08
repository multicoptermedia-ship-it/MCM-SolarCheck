import pytest
from mcm_solarcheck.review.yolo_export import yolo_detection_line, build_yolo_detection_manifest, write_yolo_detection_dataset


def test_yolo_detection_line_normalizes_reviewed_box():
    assert yolo_detection_line("hotspot",{"hotspot":0},(100,50,300,150),400,200)=="0 0.5000000000 0.5000000000 0.5000000000 0.5000000000"


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
    assert (tmp_path/"yolo"/"labels"/row["label_file"]).read_text().startswith("0 0.5000000000")


def test_yolo_manifest_requires_exact_source_dimensions():
    with pytest.raises(ValueError,match="missing source dimensions"):
        build_yolo_detection_manifest(_snapshot(),{"hotspot":0},{})


def test_yolo_manifest_groups_multiple_objects_per_source_frame(tmp_path):
    from hashlib import sha256
    source=tmp_path/"multi.jpg"; source.write_bytes(b"multi")
    digest=sha256(b"multi").hexdigest()
    manifest={"samples":[{"sample_id":"thermal:same","source_frame_id":"T1","source_file":str(source),"modality":"thermal","content_sha256":digest}],
      "labels":[
        {"label_id":1,"source_frame_id":"T1","module_id":"M1","finding_id":"F1","inspection_group_id":"flight-1","defect_class":"hotspot"},
        {"label_id":2,"source_frame_id":"T1","module_id":"M2","finding_id":"F2","inspection_group_id":"flight-1","defect_class":"hotspot"}],
      "geometries":[
        {"label_id":1,"source_frame_id":"T1","reviewer":"alice","representation":"rendered_rgb","box_xyxy":[0,0,10,10],"polygon_px":None},
        {"label_id":2,"source_frame_id":"T1","reviewer":"alice","representation":"rendered_rgb","box_xyxy":[20,20,40,40],"polygon_px":None}]}
    snap=SimpleNamespace(manifest_json=json.dumps(manifest))
    out=build_yolo_detection_manifest(snap,{"hotspot":0},{"thermal:T1":(100,100)})
    assert len(out["rows"])==1
    assert len(out["rows"][0]["labels"])==2
    write_yolo_detection_dataset(out,tmp_path/"dataset")
    text=(tmp_path/"dataset"/"labels"/out["rows"][0]["label_file"]).read_text()
    assert len(text.strip().splitlines())==2


def test_yolo_writer_tamper_fails_before_destination_mutation(tmp_path):
    from hashlib import sha256
    source=tmp_path/"source.jpg"; source.write_bytes(b"good")
    digest=sha256(b"good").hexdigest()
    out=build_yolo_detection_manifest(_snapshot(source,digest),{"hotspot":0},{"thermal:abc":(400,200)})
    source.write_bytes(b"tampered")
    destination=tmp_path/"dataset"
    with pytest.raises(ValueError,match="SHA-256 changed"):
        write_yolo_detection_dataset(out,destination)
    assert not destination.exists()


def test_yolo_class_map_requires_unique_contiguous_ids():
    with pytest.raises(ValueError,match="unique"):
        yolo_detection_line("a",{"a":0,"b":0},(0,0,1,1),10,10)
    with pytest.raises(ValueError,match="contiguous"):
        yolo_detection_line("a",{"a":1},(0,0,1,1),10,10)
