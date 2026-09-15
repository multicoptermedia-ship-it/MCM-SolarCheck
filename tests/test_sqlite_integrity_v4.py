from pathlib import Path
import sqlite3
import pytest
from mcm_solarcheck.domain.models import Finding,ThermalFrame
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.thermal.analysis import RawThermalStatistics
from mcm_solarcheck.thermal.quality import ThermalQualityGrade,ThermalQualityResult

def quality():
    return ThermalQualityResult(ThermalQualityGrade.PASS,(),RawThermalStatistics(1,1000,500,500,900,990,999))
def frame(name='a.jpg'):
    return ThermalFrame(frame_id='T-0001',source_file=Path(name),thermal_width=640,thermal_height=512,thermal_source='raw')

def test_same_frame_id_is_allowed_in_two_projects(tmp_path):
    db=ProjectDatabase(tmp_path/'x.sqlite');db.initialize();db.create_project('P1','One');db.create_project('P2','Two')
    db.save_thermal_frame('P1',frame('one.jpg'),quality());db.save_thermal_frame('P2',frame('two.jpg'),quality())
    with db.connect() as con:
        rows=con.execute("SELECT project_id,source_file FROM thermal_frames WHERE frame_id='T-0001' ORDER BY project_id").fetchall()
    assert [(r[0],r[1]) for r in rows]==[('P1','one.jpg'),('P2','two.jpg')]

def test_upsert_does_not_delete_existing_findings(tmp_path):
    db=ProjectDatabase(tmp_path/'x.sqlite');db.initialize();db.create_project('P','One')
    db.save_thermal_result('P',frame(),quality(),(Finding('F-1','T-0001',1,2),))
    db.save_thermal_frame('P',frame('updated.jpg'),quality())
    with db.connect() as con:
        assert con.execute("SELECT count(*) FROM findings WHERE project_id='P'").fetchone()[0]==1

def test_atomic_result_rolls_back_frame_when_finding_is_invalid(tmp_path):
    db=ProjectDatabase(tmp_path/'x.sqlite');db.initialize();db.create_project('P','One')
    bad=Finding('F-1','T-NOT-THIS-FRAME',1,2)
    with pytest.raises(sqlite3.IntegrityError):db.save_thermal_result('P',frame(),quality(),(bad,))
    with db.connect() as con:
        assert con.execute("SELECT count(*) FROM thermal_frames WHERE project_id='P'").fetchone()[0]==0
