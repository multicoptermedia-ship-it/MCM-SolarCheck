"""Opt-in MariaDB staging composition; never connects during construction."""
from __future__ import annotations

from mcm_solarcheck.infrastructure.mariadb_connection_factory import build_mariadb_connection_factory
from mcm_solarcheck.infrastructure.mariadb_job_lease_adapter import MariaDBJobLeaseAdapter


def build_mariadb_staging_job_leases(config, driver_connect, credentials_provider):
    factory = build_mariadb_connection_factory(config, driver_connect, credentials_provider)
    return MariaDBJobLeaseAdapter(factory)
