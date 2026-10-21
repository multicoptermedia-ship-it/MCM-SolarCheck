"""Explicit human report decision: SQLite history, invalidation and fail-closed tests."""
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.reporting.report_model import InspectionReport
from mcm_solarcheck.services.report_release import (
    latest_release_decision, record_release_decision, require_release_review,
    report_release_digest,
)
from mcm_solarcheck.services.review_progress import derive_review_progress
from mcm_solarcheck.storage.queries import InspectionSummary
from mcm_solarcheck.storage.sqlite import ProjectDatabase, SCHEMA_VERSION


def progress(project="P1", *, findings=1, open=0, confirmed=1, unclear=0, rejected=0):
    summary = InspectionSummary(
        project_id=project, rgb_frames=0, thermal_frames=0, image_pairs=0,
        pv_modules=1, findings=findings, unreviewed_findings=open,
        confirmed_findings=confirmed, rejected_findings=rejected,
        unclear_findings=unclear, calibrated_findings=0,
    )
    return derive_review_progress(summary)


def draft(project="P1", report_id="R"):
    return InspectionReport(
        report_id, project, "Synthetischer Kunde", "Solarpark",
        datetime(2026, 10, 21, 9, tzinfo=timezone.utc),
        "Prueferin", 1, 0, 0,
    )


def storage(tmp_path):
    db = ProjectDatabase(tmp_path / "release.sqlite")
    db.initialize()
    db.create_project("P1", "Projekt 1")
    db.create_project("P2", "Projekt 2")
    return db


def test_migration_from_v17_creates_empty_approval_history(tmp_path):
    db = storage(tmp_path)
    with db.connect() as sql:
        sql.execute("DROP TABLE report_release_decisions")
        sql.execute("UPDATE schema_info SET version=17")
    db.initialize()
    with db.connect() as sql:
        assert sql.execute("SELECT version FROM schema_info").fetchone()[0] == SCHEMA_VERSION == 19
        assert sql.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 2
        assert sql.execute("SELECT COUNT(*) FROM report_release_decisions").fetchone()[0] == 0


def test_never_infer_approval_from_a_complete_review(tmp_path):
    db = storage(tmp_path)
    with db.connect() as sql:
        assert latest_release_decision(sql, draft()) is None
    with pytest.raises(ValueError, match="no findings"):
        require_release_review(
            progress(findings=0, confirmed=0), acknowledge_unclear=False, followup_note="",
        )
    with pytest.raises(ValueError, match="all findings"):
        require_release_review(
            progress(findings=2, open=1), acknowledge_unclear=True, followup_note="ok",
        )


def test_unclear_is_documented_but_requires_explicit_followup(tmp_path):
    db = storage(tmp_path)
    status = progress(findings=2, confirmed=1, unclear=1)
    with db.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match="follow-up note"):
            record_release_decision(
                sql, draft(), status, approved_by="Prueferin",
            )
        assert sql.execute("SELECT COUNT(*) FROM report_release_decisions").fetchone()[0] == 0
        result = record_release_decision(
            sql, draft(), status, approved_by="Prueferin",
            acknowledge_unclear=True, followup_note="Nachmessung geplant",
        )
        assert result.unclear_count == 1
        assert result.followup_note == "Nachmessung geplant"
    with db.connect() as sql:
        assert latest_release_decision(sql, draft()) == result
        assert latest_release_decision(sql, draft(report_id="R2")) is None
        assert latest_release_decision(sql, draft(project="P2")) is None


def test_append_only_and_stale_evidence_invalidates_current_release(tmp_path):
    db = storage(tmp_path)
    with db.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        before = record_release_decision(
            sql, draft(), progress(), approved_by="Prueferin",
        )
    with db.connect() as sql:
        assert latest_release_decision(sql, draft()) == before
        original_digest = report_release_digest(sql, draft())
    db.create_project("P1", "Projekt 1 nach Prüfung")
    with db.connect() as sql:
        assert report_release_digest(sql, draft()) != original_digest
        assert latest_release_decision(sql, draft()) is None
        sql.execute("BEGIN IMMEDIATE")
        after = record_release_decision(
            sql, draft(), progress(), approved_by="Andere Fachperson",
        )
        assert after.approval_id > before.approval_id
    with db.connect() as sql:
        assert latest_release_decision(sql, draft()) == after
        assert sql.execute("SELECT COUNT(*) FROM report_release_decisions").fetchone()[0] == 2


@pytest.mark.parametrize("expert", ("", " ", "\n", "x" * 121))
def test_invalid_expert_never_creates_decision(tmp_path, expert):
    db = storage(tmp_path)
    with pytest.raises(ValueError, match="expert name|reviewer identifier"):
        with db.connect() as sql:
            sql.execute("BEGIN IMMEDIATE")
            record_release_decision(
                sql, draft(), progress(), approved_by=expert,
            )
    with db.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM report_release_decisions").fetchone()[0] == 0


def test_cross_project_progress_cannot_sign_another_project(tmp_path):
    db = storage(tmp_path)
    with pytest.raises(ValueError, match="mismatch"):
        with db.connect() as sql:
            sql.execute("BEGIN IMMEDIATE")
            record_release_decision(
                sql, draft(), progress(project="P2"), approved_by="Prueferin",
            )

def test_v18_migration_preserves_legacy_approval_without_claiming_preview(tmp_path):
    db = storage(tmp_path)
    with db.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        old = record_release_decision(
            sql, draft(), progress(), approved_by="Altpruefer",
        )
        sql.execute("DELETE FROM report_release_read_audit")
        sql.execute("DROP TABLE report_release_read_audit")
        sql.execute("UPDATE schema_info SET version=18")
    db.initialize()
    with db.connect() as sql:
        assert sql.execute("SELECT version FROM schema_info").fetchone()[0] == 19
        assert latest_release_decision(sql, draft()) == old
        assert sql.execute("SELECT COUNT(*) FROM report_release_read_audit").fetchone()[0] == 0


def test_preview_end_false_and_true_are_distinct_private_events(tmp_path):
    db = storage(tmp_path)
    with db.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        first = record_release_decision(sql, draft(), progress(),
                                        approved_by="A", reached_preview_end=False)
        second = record_release_decision(sql, draft(report_id="R2"), progress(),
                                         approved_by="B", reached_preview_end=True)
        values = sql.execute(
            "SELECT approval_id,reached_preview_end FROM report_release_read_audit "
            "ORDER BY approval_id"
        ).fetchall()
        assert [tuple(row) for row in values] == [
            (first.approval_id, 0), (second.approval_id, 1),
        ]
        assert not hasattr(first, "reached_preview_end")
        with pytest.raises(TypeError, match="boolean"):
            record_release_decision(sql, draft(report_id="R3"), progress(),
                                    approved_by="C", reached_preview_end=1)


def test_only_authenticated_admin_may_retrieve_private_scroll_history(tmp_path):
    from mcm_solarcheck.services.authorized_grant_administration import GrantAdministrator
    from mcm_solarcheck.services.report_preview_audit_admin import AuthorizedReportPreviewAudit
    db = storage(tmp_path)
    with db.connect() as sql:
        sql.execute("BEGIN IMMEDIATE")
        record_release_decision(sql, draft(), progress(), approved_by="A",
                                reached_preview_end=True)
        record_release_decision(sql, draft(project="P2"), progress(project="P2"),
                                approved_by="B", reached_preview_end=False)
    checker = AuthorizedReportPreviewAudit(db)
    for identity in (
        None,
        GrantAdministrator("user", False, frozenset({"report_release:audit_read"})),
        GrantAdministrator("user", True, frozenset()),
        GrantAdministrator("", True, frozenset({"report_release:audit_read"})),
    ):
        with pytest.raises(PermissionError):
            checker.inspect(identity, "P1")
    admin = GrantAdministrator("verified-admin", True,
                               frozenset({"report_release:audit_read"}))
    audit = checker.inspect(admin, "P1")
    assert len(audit) == 1
    assert audit[0].report_id == "R"
    assert audit[0].reached_preview_end is True
    assert checker.inspect(admin, "P2")[0].reached_preview_end is False
    with pytest.raises(KeyError):
        checker.inspect(admin, "nonexistent")
