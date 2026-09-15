import sqlite3
from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.storage.queries import InspectionQueries
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def linked_finding():
    return Finding('F-1','T-1',10,20,module_id='M-1',metadata={
        'cross_sensor_status':'assigned','rgb_frame_id':'V-1','pair_id':'P-1',
        'pair_confidence':'0.990000','rgb_pixel_x':'123.5','rgb_pixel_y':'456.5',
        'transform_method':'homography','transform_validated':'true','transform_error_px':'2.5'
    })


def prepare(db):
    db.initialize();db.create_project('P','Project')
    with db.connect() as con:
        con.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES ('P','T-1','T.JPG','m3t_app3','{}')")


def test_save_findings_atomically_persists_sensor_link(tmp_path):
    db=ProjectDatabase(tmp_path/'p.db');prepare(db);db.save_findings('P',(linked_finding(),))
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM findings WHERE project_id='P'").fetchone()[0]==1
        row=con.execute("SELECT * FROM finding_sensor_links WHERE project_id='P' AND finding_id='F-1'").fetchone()
    assert row['rgb_frame_id']=='V-1';assert row['status']=='assigned';assert row['transform_validated']==1


def test_finding_query_returns_structured_rgb_thermal_evidence(tmp_path):
    db=ProjectDatabase(tmp_path/'p.db');prepare(db);db.save_findings('P',(linked_finding(),))
    record=InspectionQueries(db).findings('P')[0]
    assert record.module_id=='M-1';assert record.rgb_frame_id=='V-1';assert record.pair_id=='P-1'
    assert record.pair_confidence==0.99;assert record.rgb_pixel_x==123.5;assert record.rgb_pixel_y==456.5
    assert record.transform_validated is True;assert record.transform_error_px==2.5;assert record.cross_sensor_status=='assigned'


def test_failed_sensor_link_rolls_back_finding_write(tmp_path):
    db=ProjectDatabase(tmp_path/'p.db');prepare(db)
    bad=Finding('F-1','T-1',10,20,metadata={'cross_sensor_status':'assigned','rgb_frame_id':'V-1','pair_confidence':'not-a-number'})
    try:db.save_findings('P',(bad,))
    except ValueError:pass
    else:raise AssertionError('invalid sensor link should fail')
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM findings WHERE project_id='P'").fetchone()[0]==0
