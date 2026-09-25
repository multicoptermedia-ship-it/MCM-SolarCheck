import json
from PIL import Image
from mcm_solarcheck.reporting.report_assets import build_detail_assets
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def test_assets_keep_unvalidated_rgb_out_and_preserve_original(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","x")
    thermal=tmp_path/"thermal.png"; rgb=tmp_path/"rgb.png"
    Image.new("RGB",(100,80)).save(thermal); Image.new("RGB",(400,300)).save(rgb)
    before=thermal.read_bytes()
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,width,height,thermal_source,metadata_json) VALUES('P','T',?,100,80,'test','{}')",(str(thermal),))
        sql.execute("INSERT INTO image_frames(project_id,frame_id,source_file,width,height,metadata_json) VALUES('P','R',?,400,300,'{}')",(str(rgb),))
        sql.execute("INSERT INTO pv_modules(project_id,module_id,frame_id,polygon_json,detector,metadata_json) VALUES('P','M','T',?,'test','{}')",(json.dumps([[10,10],[30,10],[30,30],[10,30]]),))
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,module_id,reviewer_status,metadata_json) VALUES('P','F','T',20,20,'hotspot_candidate','M','confirmed','{}')")
        sql.execute("INSERT INTO finding_sensor_links(project_id,finding_id,rgb_frame_id,rgb_pixel_x,rgb_pixel_y,transform_method,transform_validated,status,candidates_json) VALUES('P','F','R',200,150,'homography',0,'candidate','[]')")
    assets=build_detail_assets(db,"P","F","M",tmp_path/"report-assets")
    assert [a.modality for a in assets]==["thermal"]
    assert assets[0].geometry_source=="persisted_module_polygon"
    assert thermal.read_bytes()==before
    assert assets[0].path.is_file()


def test_assets_include_rgb_only_after_transform_validation(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","x")
    thermal=tmp_path/"thermal.png"; rgb=tmp_path/"rgb.png"
    Image.new("RGB",(100,80)).save(thermal); Image.new("RGB",(400,300)).save(rgb)
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,width,height,thermal_source,metadata_json) VALUES('P','T',?,100,80,'test','{}')",(str(thermal),))
        sql.execute("INSERT INTO image_frames(project_id,frame_id,source_file,width,height,metadata_json) VALUES('P','R',?,400,300,'{}')",(str(rgb),))
        sql.execute("INSERT INTO pv_modules(project_id,module_id,frame_id,polygon_json,detector,metadata_json) VALUES('P','M','T',?,'test','{}')",(json.dumps([[10,10],[30,10],[30,30],[10,30]]),))
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,module_id,reviewer_status,metadata_json) VALUES('P','F','T',20,20,'hotspot_candidate','M','confirmed','{}')")
        sql.execute("INSERT INTO finding_sensor_links(project_id,finding_id,rgb_frame_id,rgb_pixel_x,rgb_pixel_y,transform_method,transform_validated,status,candidates_json) VALUES('P','F','R',200,150,'homography',1,'validated','[]')")
    assets=build_detail_assets(db,"P","F","M",tmp_path/"report-assets")
    assert [a.modality for a in assets]==["rgb","thermal"]
    assert assets[0].geometry_source=="validated_cross_sensor:homography"


def test_missing_crop_source_is_skipped_without_fabricating_asset(tmp_path):
    db=_db(tmp_path)
    missing=tmp_path/"missing-thermal.png"
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,width,height,thermal_source,metadata_json) VALUES('P1','T1',?,100,100,'test','{}')",(str(missing),))
        sql.execute("INSERT INTO pv_modules(project_id,module_id,frame_id,polygon_json,detector,metadata_json) VALUES('P1','M1','T1','[[10,10],[30,10],[30,30],[10,30]]','test','{}')")
    assets=build_detail_assets(db,"P1","F1","M1",tmp_path/"assets")
    assert assets==()
    assert not (tmp_path/"assets").exists()
