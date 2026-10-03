import json
from mcm_solarcheck.reporting.crop_planner import thermal_module_crop_plan, rgb_finding_crop_plan
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _db(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P","x"); return db


def test_thermal_crop_uses_polygon_from_exact_thermal_frame(tmp_path):
    db=_db(tmp_path)
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,width,height,thermal_source,metadata_json) VALUES('P','T','thermal.jpg',100,80,'test','{}')")
        sql.execute("INSERT INTO pv_modules(project_id,module_id,frame_id,polygon_json,detector,metadata_json) VALUES('P','M','T',?,'test','{}')",(json.dumps([[10,10],[30,10],[30,30],[10,30]]),))
    plan=thermal_module_crop_plan(db,"P","M")
    assert plan.modality=="thermal" and plan.source_frame_id=="T"
    assert plan.geometry_source=="persisted_module_polygon"


def test_rgb_crop_requires_validated_cross_sensor_projection(tmp_path):
    db=_db(tmp_path)
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P','T','thermal.jpg','test','{}')")
        sql.execute("INSERT INTO image_frames(project_id,frame_id,source_file,width,height,metadata_json) VALUES('P','R','rgb.jpg',400,300,'{}')")
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,reviewer_status,metadata_json) VALUES('P','F','T',1,2,'hotspot_candidate','confirmed','{}')")
        sql.execute("INSERT INTO finding_sensor_links(project_id,finding_id,rgb_frame_id,rgb_pixel_x,rgb_pixel_y,transform_method,transform_validated,status,candidates_json) VALUES('P','F','R',200,150,'homography',0,'candidate','[]')")
    assert rgb_finding_crop_plan(db,"P","F") is None
    with db.connect() as sql: sql.execute("UPDATE finding_sensor_links SET transform_validated=1,status='validated' WHERE project_id='P' AND finding_id='F'")
    plan=rgb_finding_crop_plan(db,"P","F")
    assert plan.modality=="rgb" and plan.source_frame_id=="R"
    assert plan.geometry_source=="validated_cross_sensor:homography"
