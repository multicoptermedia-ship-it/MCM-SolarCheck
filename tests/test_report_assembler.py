from mcm_solarcheck.domain.operator_profile import OperatorProfile
from datetime import datetime, timezone
import pytest
from mcm_solarcheck.domain.models import Finding, PVModule
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.reporting.report_assembler import assemble_inspection_report
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _db(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P1","Inspection")
    db.save_project_profile("P1",ProjectProfile("Customer","Site","Street 1","12345","Town","Inspector",customer_contact="Contact",order_reference="ORDER-1"))
    return db


def test_assembler_reuses_project_profile_and_confirmed_module(tmp_path):
    db=_db(tmp_path)
    db.save_modules("P1",(PVModule("M1","T1",((0,0),(1,0),(1,1)),0.9,"test"),))
    # Report evidence requires a persisted thermal frame, so use direct DB fixture rows for this contract test.
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','t.jpg','test','{}')")
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,module_id,reviewer_status,metadata_json) VALUES('P1','F1','T1',1,2,'hotspot_candidate','M1','confirmed','{}')")
        sql.execute("INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc) VALUES('P1','F1','confirmed','Inspector','2026-09-24T12:00:00+00:00')")
    report=assemble_inspection_report(db,"P1","R1",datetime(2026,9,24,12,tzinfo=timezone.utc))
    assert report.customer_name=="Customer"; assert report.site_address=="Street 1, 12345, Town"
    assert report.order_reference=="ORDER-1"; assert report.details[0].module_id=="M1"


def test_released_report_fails_closed_on_unreviewed_finding(tmp_path):
    db=_db(tmp_path)
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','t.jpg','test','{}')")
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,reviewer_status,metadata_json) VALUES('P1','F1','T1',1,2,'hotspot_candidate','unreviewed','{}')")
    with pytest.raises(ValueError,match="reviewed findings"):
        assemble_inspection_report(db,"P1","R1",datetime(2026,9,24,12,tzinfo=timezone.utc),release_status="released")


def test_multiple_confirmed_findings_on_same_module_count_once(tmp_path):
    db=_db(tmp_path)
    db.save_modules("P1",(PVModule("M1","T1",((0,0),(1,0),(1,1)),0.9,"test"),))
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','t.jpg','test','{}')")
        for finding_id,kind in (("F1","hotspot_candidate"),("F2","open_circuit_candidate")):
            sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,module_id,reviewer_status,metadata_json) VALUES('P1',?,?,1,2,?,'M1','confirmed','{}')",(finding_id,"T1",kind))
            sql.execute("INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc) VALUES('P1',?,'confirmed','Inspector','2026-09-24T12:00:00+00:00')",(finding_id,))
    report=assemble_inspection_report(db,"P1","R1",datetime(2026,9,24,12,tzinfo=timezone.utc))
    assert len(report.details)==2
    assert report.conspicuous_modules==1


def test_unclear_findings_on_same_module_create_one_manual_review_detail(tmp_path):
    db=_db(tmp_path)
    db.save_modules("P1",(PVModule("M1","T1",((0,0),(1,0),(1,1)),0.9,"test"),))
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','t.jpg','test','{}')")
        for finding_id in ("U1","U2"):
            sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,module_id,reviewer_status,metadata_json) VALUES('P1',?,?,1,2,'hotspot_candidate','M1','unclear','{}')",(finding_id,"T1"))
    report=assemble_inspection_report(db,"P1","R1",datetime(2026,9,24,12,tzinfo=timezone.utc))
    assert report.manual_review_modules==1
    assert len(report.details)==1
    assert report.details[0].module_id=="M1"
    assert report.details[0].finding_label is None
    assert report.details[0].manual_inspection_required is True


def test_unresolved_confirmed_finding_does_not_fake_module_count_and_blocks_release(tmp_path):
    db=_db(tmp_path)
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','t.jpg','test','{}')")
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,reviewer_status,metadata_json) VALUES('P1','F1','T1',1,2,'hotspot_candidate','confirmed','{}')")
        sql.execute("INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc) VALUES('P1','F1','confirmed','Inspector','2026-09-24T12:00:00+00:00')")
    draft=assemble_inspection_report(db,"P1","R1",datetime(2026,9,24,12,tzinfo=timezone.utc))
    assert draft.conspicuous_modules==0
    assert draft.manual_review_modules==0
    assert draft.details==()
    with pytest.raises(ValueError,match="resolved physical modules"):
        assemble_inspection_report(db,"P1","R2",datetime(2026,9,24,12,tzinfo=timezone.utc),release_status="released")


def test_assembler_attaches_only_persisted_paired_rgb_and_thermal_sources(tmp_path):
    db=_db(tmp_path)
    db.save_modules("P1",(PVModule("M1","T1",((0,0),(1,0),(1,1)),0.9,"test"),))
    with db.connect() as sql:
        sql.execute("INSERT INTO image_frames(project_id,frame_id,source_file,metadata_json) VALUES('P1','R1','rgb.jpg','{}')")
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','thermal.jpg','test','{}')")
        sql.execute("INSERT INTO image_pairs(project_id,pair_id,rgb_frame_id,thermal_frame_id,confidence,method) VALUES('P1','PAIR1','R1','T1',0.95,'timestamp')")
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,module_id,reviewer_status,metadata_json) VALUES('P1','F1','T1',1,2,'hotspot_candidate','M1','confirmed','{}')")
        sql.execute("INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc) VALUES('P1','F1','confirmed','Inspector','2026-09-24T12:00:00+00:00')")
    detail=assemble_inspection_report(db,"P1","REP",datetime(2026,9,24,12,tzinfo=timezone.utc)).details[0]
    assert detail.thermal_image.path=="thermal.jpg"
    assert detail.thermal_image.source_frame_id=="T1"
    assert detail.rgb_image.path=="rgb.jpg"
    assert detail.rgb_image.source_frame_id=="R1"
    assert detail.rgb_image.modality=="rgb" and detail.thermal_image.modality=="thermal"


def test_unresolved_unclear_finding_blocks_release_without_inventing_module(tmp_path):
    db=_db(tmp_path)
    with db.connect() as sql:
        sql.execute("INSERT INTO thermal_frames(project_id,frame_id,source_file,thermal_source,metadata_json) VALUES('P1','T1','t.jpg','test','{}')")
        sql.execute("INSERT INTO findings(project_id,finding_id,thermal_frame_id,pixel_x,pixel_y,finding_type,reviewer_status,metadata_json) VALUES('P1','U1','T1',1,2,'hotspot_candidate','unclear','{}')")
        sql.execute("INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc) VALUES('P1','U1','unclear','Inspector','2026-09-25T08:00:00+00:00')")
    draft=assemble_inspection_report(db,"P1","R1",datetime(2026,9,25,8,tzinfo=timezone.utc))
    assert draft.manual_review_modules==0
    assert draft.details==()
    with pytest.raises(ValueError,match="resolved physical modules"):
        assemble_inspection_report(db,"P1","R2",datetime(2026,9,25,8,tzinfo=timezone.utc),release_status="released")


def test_report_snapshots_operator_branding(tmp_path):
    db=_db(tmp_path)
    operator=OperatorProfile("MCM Test GmbH","Werkstr. 1","47500","Teststadt","info@example.invalid",phone="+49 1",website="https://example.invalid",vat_id="DE123",logo_path="brand.png")
    report=assemble_inspection_report(db,"P1","R1",datetime(2026,9,25,8,tzinfo=timezone.utc),operator_profile=operator)
    assert report.operator.company_name=="MCM Test GmbH"
    assert report.operator.address=="Werkstr. 1, 47500 Teststadt"
    assert report.operator.logo_path=="brand.png"
