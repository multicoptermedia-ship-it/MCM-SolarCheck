"""Fail-closed connection configuration for injected MariaDB DB-API drivers."""
from __future__ import annotations

import ssl


def mariadb_tls_context(ca_file):
    if not isinstance(ca_file, str) or not ca_file.strip():
        raise ValueError("CA certificate path required")
    context = ssl.create_default_context(cafile=ca_file)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return context


def build_mariadb_connection_factory(config, driver_connect, credentials_provider):
    """Only calls credentials provider at connection time; no eager network access.

    The injected driver must honor the ssl context and enforce hostname verification.
    """
    from mcm_solarcheck.infrastructure.mariadb_staging_config import MariaDBStagingConfig
    if not isinstance(config, MariaDBStagingConfig):
        raise TypeError("MariaDBStagingConfig required")
    if not callable(driver_connect) or not callable(credentials_provider):
        raise TypeError("driver and credentials provider must be callable")

    def connect():
        password = credentials_provider()
        if not isinstance(password, str) or not password:
            raise ValueError("password required")
        context = mariadb_tls_context(config.tls_ca_file)
        return driver_connect(
            host=config.host, port=config.port, database=config.database,
            user=config.username, password=password, ssl_context=context,
            autocommit=False,
        )

    return connect
