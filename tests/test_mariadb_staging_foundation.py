import pytest

from mcm_solarcheck.infrastructure.mariadb_staging_config import MariaDBStagingConfig
from mcm_solarcheck.infrastructure.mariadb_staging_schema import MARIADB_STAGING_SCHEMA
from mcm_solarcheck.infrastructure.mariadb_job_lease_sql import (
    CLAIM_QUEUED_JOB_SQL, RENEW_JOB_SQL, COMPLETE_JOB_SQL,
    validate_lease_seconds, affected_exactly_one,
)


def test_staging_config_accepts_provider_assigned_database_name():
    config = MariaDBStagingConfig(
        host="db123.example.test", port=3306, database="dbs987654",
        username="dbu123", tls_ca_file="/etc/ssl/ionos-ca.pem",
    )
    assert config.database == "dbs987654"


@pytest.mark.parametrize("kwargs", [
    {"host": "db;drop"}, {"database": "bad name"},
    {"port": 0}, {"port": True}, {"username": ""},
    {"tls_ca_file": ""},
])
def test_staging_config_rejects_invalid_values(kwargs):
    values = dict(host="db.example.test", port=3306, database="dbs123",
                  username="dbu123", tls_ca_file="/tmp/ca.pem")
    values.update(kwargs)
    with pytest.raises(ValueError):
        MariaDBStagingConfig(**values)


def test_schema_is_innodb_and_stores_only_file_references():
    assert len(MARIADB_STAGING_SCHEMA) == 3
    assert all("ENGINE=InnoDB" in statement for statement in MARIADB_STAGING_SCHEMA)
    assert "storage_key" in MARIADB_STAGING_SCHEMA[2]
    assert "LONGBLOB" not in " ".join(MARIADB_STAGING_SCHEMA).upper()


def test_job_leases_are_token_scoped_and_check_rowcounts():
    assert "state='queued'" in CLAIM_QUEUED_JOB_SQL
    assert "lease_token=%s" in RENEW_JOB_SQL
    assert "lease_token=%s" in COMPLETE_JOB_SQL
    assert "UTC_TIMESTAMP(6)" in RENEW_JOB_SQL
    assert affected_exactly_one(1)
    assert not affected_exactly_one(0)
    with pytest.raises(ValueError):
        validate_lease_seconds(0)
    assert validate_lease_seconds(60) == 60
