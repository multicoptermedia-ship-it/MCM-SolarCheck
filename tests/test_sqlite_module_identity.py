import sqlite3
from mcm_solarcheck.domain.models import PVModule
from mcm_solarcheck.storage.sqlite import ProjectDatabase,SCHEMA_VERSION
from mcm_solarcheck.vision.module_identity import ModuleObservation,IdentityAssignment

def test_schema_contains_structured_module_identity_links(tmp_path):
 p=tmp_path/'p.db';d=ProjectDatabase(p);d.initialize()
 with sqlite3.connect(p) as c:
  assert c.execute('select version from schema_info').fetchone()[0]==SCHEMA_VERSION
  assert c.execute("select count(*) from sqlite_master where type='table' and name='module_identity_links'").fetchone()[0]==1

def test_modules_and_physical_identity_are_persisted_atomically(tmp_path):
 p=tmp_path/'p.db';d=ProjectDatabase(p);d.initialize();d.create_project('P','x')
 m=PVModule('V-1:M-0001','V-1',((0,0),(10,0),(10,20),(0,20)),.9,'test')
 o=ModuleObservation('V-1',m.module_id,(5,10),10,20);a=IdentityAssignment(o,'M-0001','new',None)
 d.save_modules_with_identities('P',(m,),(a,))
 with sqlite3.connect(p) as c:
  assert c.execute('select count(*) from pv_modules').fetchone()[0]==1
  assert c.execute('select physical_module_id,status from module_identity_links').fetchone()==('M-0001','new')

def test_identity_persistence_rejects_unknown_local_module(tmp_path):
 p=tmp_path/'p.db';d=ProjectDatabase(p);d.initialize();d.create_project('P','x')
 o=ModuleObservation('V-X','missing',(5,10),10,20);a=IdentityAssignment(o,'M-0001','new',None)
 try:d.save_modules_with_identities('P',(),(a,))
 except ValueError:pass
 else:raise AssertionError('unknown module identity must fail closed')
