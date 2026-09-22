from mcm_solarcheck.domain.models import PVModule
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.storage.queries import InspectionQueries
from mcm_solarcheck.vision.module_identity import ModuleObservation,IdentityAssignment

def test_module_identity_roundtrip_query(tmp_path):
 d=ProjectDatabase(tmp_path/'p.db');d.initialize();d.create_project('P','x')
 m=PVModule('V:M1','V',((0,0),(10,0),(10,20),(0,20)))
 a=IdentityAssignment(ModuleObservation('V',m.module_id,(5,10),10,20),'M-0001','new',None)
 d.save_modules_with_identities('P',(m,),(a,))
 rows=InspectionQueries(d).module_identities('P')
 assert len(rows)==1 and rows[0].local_module_id=='V:M1' and rows[0].physical_module_id=='M-0001' and rows[0].status=='new'
 assert InspectionQueries(d).module_identities('P',physical_module_id='M-9999')==()
