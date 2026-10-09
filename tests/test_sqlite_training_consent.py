"""Training permission is voluntary, persistent and revocable."""
import pytest

from mcm_solarcheck.infrastructure.sqlite_training_consent import SQLiteTrainingConsentStore


def test_consent_audit_persists_and_withdrawal_disables_training(tmp_path):
    path = tmp_path / "consent.db"
    store = SQLiteTrainingConsentStore(path)
    assert not store.is_granted(customer_id="a", project_id="p")
    store.record(customer_id="a", project_id="p", event="granted", notice_version="v1")
    reopened = SQLiteTrainingConsentStore(path)
    assert reopened.is_granted(customer_id="a", project_id="p")
    assert not reopened.is_granted(customer_id="b", project_id="p")
    reopened.record(customer_id="a", project_id="p", event="withdrawn", notice_version="v1")
    assert not store.is_granted(customer_id="a", project_id="p")
    assert [row[0] for row in store.events(customer_id="a", project_id="p")] == ["granted", "withdrawn"]
    assert all(row[2].endswith("+00:00") for row in store.events(customer_id="a", project_id="p"))


@pytest.mark.parametrize("event", ["", "denied", "true"])
def test_reject_unknown_events(tmp_path, event):
    store = SQLiteTrainingConsentStore(tmp_path / "consent.db")
    with pytest.raises(ValueError):
        store.record(customer_id="a", project_id="p", event=event, notice_version="v1")
