import sqlite3

import pytest

from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.storage.sqlite import ProjectDatabase, SCHEMA_VERSION


def test_initialize_creates_current_schema_and_sensor_link_table(tmp_path):
    path=tmp_path/'project.db';db=ProjectDatabase(path);db.initialize()
    with sqlite3.connect(path) as con:
        version=con.execute('SELECT version FROM schema_info').fetchone()[0]
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert version == SCHEMA_VERSION
    assert 'finding_sensor_links' in tables


def test_initialize_refuses_old_version_without_mutating_database(tmp_path):
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE schema_info(version INTEGER NOT NULL)')
        con.execute('INSERT INTO schema_info VALUES (4)')
        con.execute('CREATE TABLE legacy_marker(value TEXT)')
        con.execute("INSERT INTO legacy_marker VALUES ('keep-me')")
    with pytest.raises(RuntimeError, match='migration required'):
        ProjectDatabase(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT value FROM legacy_marker').fetchone()[0] == 'keep-me'
        assert con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='finding_sensor_links'").fetchone()[0] == 0


def test_initialize_refuses_unversioned_nonempty_database_without_mutation(tmp_path):
    path=tmp_path/'unknown.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE customer_data(value TEXT)')
    with pytest.raises(RuntimeError, match='Unversioned'):
        ProjectDatabase(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='schema_info'").fetchone()[0] == 0


def test_cross_sensor_link_is_stored_as_structured_columns(tmp_path):
    path=tmp_path/'project.db';db=ProjectDatabase(path);db.initialize();db.create_project('P','Test')
    finding=Finding('F-1','T-1',10,20,metadata={
        'cross_sensor_status':'assigned','rgb_frame_id':'V-1','pair_id':'PAIR-1',
        'pair_confidence':'1.000000','rgb_pixel_x':'123.500','rgb_pixel_y':'456.250',
        'transform_method':'homography','transform_validated':'true','transform_error_px':'2.500',
        'cross_sensor_candidates':'M-0042',
    })
    # Satisfy the FK with a minimal thermal frame/finding row using direct setup;
    # this test isolates the structured link persistence contract.
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source) VALUES ('P','T-1','T.JPG','raw')")
        con.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,reviewer_status) VALUES ('P','F-1','T-1',10,20,'candidate','unreviewed')")
    db.save_finding_sensor_link('P',finding)
    with sqlite3.connect(path) as con:
        row=con.execute('SELECT rgb_frame_id,pair_id,pair_confidence,rgb_pixel_x,rgb_pixel_y,transform_method,transform_validated,transform_error_px,status,candidates_json FROM finding_sensor_links').fetchone()
    assert row[:9] == ('V-1','PAIR-1',1.0,123.5,456.25,'homography',1,2.5,'assigned')
    assert 'M-0042' in row[9]
