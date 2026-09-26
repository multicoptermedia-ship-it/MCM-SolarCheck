import sqlite3
from pathlib import Path
from mcm_solarcheck.domain.models import ImageFrame,ImagePair,PVModule,Position,ThermalFrame
from mcm_solarcheck.importers.project import ProjectImportResult
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService

def test_project_import_counts_unpaired_frames():
    rgb=(ImageFrame('V-1',Path('a.JPG')),ImageFrame('V-2',Path('b.JPG')))
    class Batch:results=(type('R',(),{'frame':ThermalFrame('T-1',Path('t.JPG'))})(),)
    result=ProjectImportResult(rgb,Batch(),(ImagePair('P','V-1','T-1',1.0,'sequence'),))
    assert result.unpaired_rgb_count==1;assert result.unpaired_thermal_count==0

def test_sqlite_v4_persists_rgb_pair_and_module(tmp_path):
    db=ProjectDatabase(tmp_path/'project.sqlite');db.initialize();db.create_project('P-1','PV Test')
    rgb=ImageFrame('V-0001',Path('V.JPG'),width=4000,height=3000,position=Position(51.0,6.5));db.save_image_frames('P-1',(rgb,))
    with db.connect() as con:
        con.execute('INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source) VALUES (?,?,?,?)',('P-1','T-0001','T.JPG','fixture'))
    pair=ImagePair('PAIR-1','V-0001','T-0001',0.99,'sequence+time+position',0.22,0.158)
    module=PVModule('T-0001:M-0001','T-0001',((10,10),(100,10),(100,80),(10,80)),0.94,'fixture')
    db.save_pairs('P-1',(pair,));db.save_modules('P-1',(module,))
    con=sqlite3.connect(db.path);con.row_factory=sqlite3.Row
    assert con.execute("SELECT COUNT(*) FROM image_frames WHERE project_id='P-1'").fetchone()[0]==1
    stored_pair=con.execute("SELECT * FROM image_pairs WHERE project_id='P-1'").fetchone();assert stored_pair['confidence']==0.99;assert stored_pair['distance_m']==0.22
    stored_module=con.execute("SELECT * FROM pv_modules WHERE project_id='P-1'").fetchone();assert stored_module['detector']=='fixture';assert '100' in stored_module['polygon_json'];con.close()


def test_application_service_lists_only_persisted_projects(tmp_path):
    db=ProjectDatabase(tmp_path/'projects.sqlite');db.initialize()
    service=ProjectApplicationService(db)
    assert service.projects()==()
    db.create_project('P-1','PV Test')
    projects=service.projects()
    assert len(projects)==1
    assert projects[0].project_id=='P-1'
    assert projects[0].name=='PV Test'


def test_application_service_opens_only_persisted_project(tmp_path):
    db=ProjectDatabase(tmp_path/'open.sqlite');db.initialize()
    db.create_project('P-OPEN','Persisted')
    service=ProjectApplicationService(db)

    state=service.open_project('P-OPEN')

    assert state==service.state('P-OPEN')


def test_application_service_rejects_unknown_project_open(tmp_path):
    db=ProjectDatabase(tmp_path/'open.sqlite');db.initialize()
    service=ProjectApplicationService(db)

    try:
        service.open_project('P-INVENTED')
    except KeyError as error:
        assert 'Unknown project: P-INVENTED' in str(error)
    else:
        raise AssertionError('unknown project must fail closed')


def test_application_service_creates_persisted_project(tmp_path):
    db=ProjectDatabase(tmp_path/'create.sqlite');db.initialize()
    service=ProjectApplicationService(db)

    project=service.create_project(' P-NEW ', ' Neuer Solarpark ')

    assert project.project_id=='P-NEW'
    assert project.name=='Neuer Solarpark'
    assert [(p.project_id,p.name) for p in service.projects()]==[('P-NEW','Neuer Solarpark')]


def test_application_service_rejects_invalid_or_duplicate_project_creation(tmp_path):
    db=ProjectDatabase(tmp_path/'create.sqlite');db.initialize()
    service=ProjectApplicationService(db)

    for project_id,name in (('', 'Solarpark'), ('P-1', '   ')):
        try:
            service.create_project(project_id,name)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid project creation must fail closed')

    service.create_project('P-1','Original')
    try:
        service.create_project('P-1','Replacement')
    except ValueError as error:
        assert 'Project already exists: P-1' in str(error)
    else:
        raise AssertionError('duplicate project creation must fail closed')

    assert service.projects()[0].name=='Original'
