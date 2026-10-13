"""Opt-in composition for bounded admission and paired lease lifecycle."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.mariadb_bounded_job_admission import MariaDBBoundedJobAdmission
from mcm_solarcheck.infrastructure.mariadb_bounded_job_lifecycle import MariaDBBoundedJobLifecycle
from mcm_solarcheck.infrastructure.mariadb_connection_factory import build_mariadb_connection_factory


@dataclass(frozen=True)
class MariaDBBoundedWorkers:
    admission: MariaDBBoundedJobAdmission
    lifecycle: MariaDBBoundedJobLifecycle


def build_mariadb_bounded_workers(config, driver_connect, credentials_provider):
    factory = build_mariadb_connection_factory(config, driver_connect, credentials_provider)
    return MariaDBBoundedWorkers(
        admission=MariaDBBoundedJobAdmission(factory),
        lifecycle=MariaDBBoundedJobLifecycle(factory),
    )
