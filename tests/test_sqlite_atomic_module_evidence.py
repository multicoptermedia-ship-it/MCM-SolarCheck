import sqlite3
from mcm_solarcheck.domain.models import PVModule,Finding
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.vision.module_identity import ModuleObservation,IdentityAssignment

def test_atomic_module_identity_finding_and_sensor_link(tmp_path):
 p=tmp_path/'p.db';d=ProjectDatabase(p);d.initialize();d.create_project('P','x')
 with sqlite3.connect(p) as c:c.execute("insert into thermal_frames(project_id,frame_id,source_file,thermal_source) values('P','T','t.jpg','raw')")
 m=PVModule('V:M-0001','V',((0,0),(10,0),(10,20),(0,20)),.9,'test')
 a=IdentityAssignment(ModuleObservation('V',m.module_id,(5,10),10,20),'M-0001','new',None)
 f=Finding('F','T',1,2,module_id=m.module_id,metadata={'cross_sensor_status':'assigned','rgb_frame_id':'V','transform_method':'test','transform_validated':'true'})
 d.save_modules_identities_and_findings('P',(m,),(a,),(f,))
 with sqlite3.connect(p) as c:
  assert c.execute('select count(*) from pv_modules').fetchone()[0]==1
  assert c.execute('select count(*) from module_identity_links').fetchone()[0]==1
  assert c.execute('select count(*) from findings').fetchone()[0]==1
  assert c.execute('select count(*) from finding_sensor_links').fetchone()[0]==1

def test_atomic_evidence_rejects_external_module_reference_without_writes(tmp_path):
 p=tmp_path/'p.db';d=ProjectDatabase(p);d.initialize();d.create_project('P','x')
 f=Finding('F','T',1,2,module_id='missing')
 try:d.save_modules_identities_and_findings('P',(),(),(f,))
 except ValueError:pass
 else:raise AssertionError('must fail closed')
 with sqlite3.connect(p) as c:assert c.execute('select count(*) from pv_modules').fetchone()[0]==0 and c.execute('select count(*) from findings').fetchone()[0]==0
