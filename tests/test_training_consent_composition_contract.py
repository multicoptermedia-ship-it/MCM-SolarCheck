"""Ensure the real online composition connects the durable consent audit."""
from pathlib import Path


def test_online_persistence_creates_training_consent_store():
    source = Path("src/mcm_solarcheck/infrastructure/online_persistence.py").read_text(encoding="utf-8")
    assert "training_consents=SQLiteTrainingConsentStore(database)" in source


def test_online_composition_checks_project_owner():
    source = Path("src/mcm_solarcheck/services/online_composition.py").read_text(encoding="utf-8")
    assert "TrainingConsentService(persistence.training_consents, persistence.projects.project_belongs_to_customer)" in source


def test_http_uses_composed_service():
    source = Path("src/mcm_solarcheck/online/http_entrypoint.py").read_text(encoding="utf-8")
    assert "getattr(product.services, 'training_consent', None)" in source
