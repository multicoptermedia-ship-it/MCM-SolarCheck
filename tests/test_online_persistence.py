from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from mcm_solarcheck.infrastructure.online_persistence import build_online_persistence
from mcm_solarcheck.infrastructure.online_private_paths import OnlinePrivatePaths
from mcm_solarcheck.infrastructure.smtp_email import SMTPConfig, SMTPSecurity


class FakeSecretStore:
    def is_set(self) -> bool:
        return False

    def replace(self, password: str) -> None:
        pass

    def resolve_for_delivery(self) -> str:
        raise RuntimeError("SMTP password is not configured")


def test_online_persistence_uses_one_private_state_database(tmp_path) -> None:
    private = tmp_path / "private"
    paths = OnlinePrivatePaths(
        private / "state" / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
        tmp_path / "public",
    )

    persistence = build_online_persistence(
        paths,
        smtp_default=SMTPConfig(
            "smtp.example.invalid",
            465,
            "solarcheck@example.invalid",
            security=SMTPSecurity.TLS,
        ),
        smtp_secrets=FakeSecretStore(),
    )

    database_backed = (
        persistence.registrations,
        persistence.compute_jobs,
        persistence.billing,
        persistence.payments,
        persistence.payment_operations,
        persistence.payment_authorizations,
        persistence.sepa_mandates,
        persistence.sepa_submissions,
        persistence.sepa_collections,
        persistence.invoice_identity,
        persistence.invoice_delivery,
        persistence.report_recovery,
        persistence.smtp_settings,
        persistence.smtp_admin_audit,
    )
    assert {store.database for store in database_backed} == {str(paths.state_database)}
    assert persistence.projects.path == paths.state_database
    assert persistence.reports.root == paths.reports_root
    assert persistence.invoices.root == paths.invoices_root
    assert persistence.smtp_secrets.is_set() is False
    assert paths.reports_root.is_dir()
    assert paths.invoices_root.is_dir()
    assert paths.uploads_root.is_dir()

    with sqlite3.connect(paths.state_database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "projects",
        "project_profiles",
        "online_registrations",
        "email_verifications",
        "registration_notification_outbox",
        "compute_jobs",
        "compute_job_billing",
        "online_payments",
        "payment_operation_intents",
        "payment_authorization_intents",
        "sepa_mandates",
        "sepa_submissions",
        "sepa_collections",
        "invoice_identity",
        "invoice_admin_delivery",
        "report_recovery_notification",
        "smtp_settings",
        "smtp_admin_audit",
    } <= tables


def test_online_persistence_requires_validated_private_paths(tmp_path) -> None:
    with pytest.raises(TypeError, match="OnlinePrivatePaths"):
        build_online_persistence(
            tmp_path,  # type: ignore[arg-type]
            smtp_default=SMTPConfig(
                "smtp.example.invalid",
                465,
                "solarcheck@example.invalid",
                security=SMTPSecurity.TLS,
            ),
            smtp_secrets=FakeSecretStore(),
        )


def test_online_persistence_requires_explicit_smtp_configuration(tmp_path) -> None:
    private = tmp_path / "private"
    paths = OnlinePrivatePaths(
        private / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
    )

    with pytest.raises(TypeError, match="smtp_default"):
        build_online_persistence(
            paths,
            smtp_default=None,  # type: ignore[arg-type]
            smtp_secrets=FakeSecretStore(),
        )


def test_online_persistence_requires_explicit_smtp_secret_backend(tmp_path) -> None:
    private = tmp_path / "private"
    paths = OnlinePrivatePaths(
        private / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
    )

    with pytest.raises(TypeError):
        build_online_persistence(
            paths,
            smtp_default=SMTPConfig(
                "smtp.example.invalid",
                465,
                "solarcheck@example.invalid",
                security=SMTPSecurity.TLS,
            ),
        )


def test_online_persistence_includes_registration_and_compute_job_state(tmp_path) -> None:
    private = tmp_path / "private"
    paths = OnlinePrivatePaths(
        private / "solarcheck.sqlite",
        private / "reports",
        private / "invoices",
        tmp_path / "public",
    )
    persistence = build_online_persistence(
        paths,
        smtp_default=SMTPConfig(
            "smtp.example.invalid",
            465,
            "solarcheck@example.invalid",
            security=SMTPSecurity.TLS,
        ),
        smtp_secrets=FakeSecretStore(),
    )
    from mcm_solarcheck.services.compute_jobs import ComputeJob, ComputeJobStatus
    from mcm_solarcheck.services.registration import OnlineRegistration

    persistence.registrations.create(
        OnlineRegistration(
            "user-e2e",
            "E2E User",
            "e2e@example.invalid",
            street="Testweg 1",
            postal_code="50181",
            city="Bedburg",
        ),
        token="verification-token",
        expires_at=datetime(2026, 10, 2, 13, 0, tzinfo=timezone.utc),
    )
    persistence.compute_jobs.create(
        ComputeJob(
            "job-e2e",
            "user-e2e",
            "project-e2e",
            ComputeJobStatus.QUEUED,
        )
    )

    assert persistence.registrations.get("user-e2e").user_id == "user-e2e"
    assert persistence.compute_jobs.get("job-e2e").status is ComputeJobStatus.QUEUED


def test_online_persistence_project_state_uses_private_state_database(tmp_path) -> None:
    private=tmp_path/"private"
    paths=OnlinePrivatePaths(
        private/"state"/"solarcheck.sqlite",
        private/"reports",
        private/"invoices",
        tmp_path/"public",
    )
    persistence=build_online_persistence(
        paths,
        smtp_default=SMTPConfig(
            "smtp.example.invalid",465,"solarcheck@example.invalid",
            security=SMTPSecurity.TLS,
        ),
        smtp_secrets=FakeSecretStore(),
    )

    persistence.projects.create_project("P-ONLINE","Online Project")

    assert persistence.projects.path==paths.state_database
    with sqlite3.connect(paths.state_database) as connection:
        assert connection.execute(
            "SELECT name FROM projects WHERE project_id=?",
            ("P-ONLINE",),
        ).fetchone()==("Online Project",)
