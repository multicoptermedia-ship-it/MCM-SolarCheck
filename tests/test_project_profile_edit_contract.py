"""SQLite project master-data edits: atomic, project-scoped, non-destructive."""
from dataclasses import replace

import pytest

from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def seeded_service(tmp_path):
    database = ProjectDatabase(tmp_path / "master-data.sqlite3")
    database.initialize()
    service = ProjectApplicationService(database)
    service.create_project("P1", "Solarfeld")
    service.create_project("P2", "Dachanlage")
    profile = ProjectProfile(
        customer_name="Fiktiver Kunde", site_name="Solarpark Nord",
        site_street="Musterweg 1", site_postal_code="12345",
        site_city="Musterstadt", inspector="Pruefer A",
        site_timezone="Europe/Berlin",
        customer_contact="Kontakt bleibt erhalten",
        customer_email="synthetisch@example.invalid",
        order_reference="AUFTRAG-4711",
    )
    service.save_project_profile("P1", profile)
    service.save_project_profile("P2", replace(profile, site_name="Anderes Dach"))
    return service, profile


def test_persisted_profile_edit_preserves_optional_fields_and_other_project(tmp_path):
    service, before = seeded_service(tmp_path)
    other = service.project_profile("P2")
    updated = replace(before, site_name="Solarpark Sued", inspector="Pruefer B")
    assert service.update_project_profile_if_unchanged("P1", before, updated) is True
    assert service.project_profile("P1") == updated
    assert service.project_profile("P1").order_reference == "AUFTRAG-4711"
    assert service.project_profile("P1").customer_email == "synthetisch@example.invalid"
    assert service.project_profile("P2") == other


def test_stale_dialog_cannot_overwrite_newer_persisted_master_data(tmp_path):
    service, original = seeded_service(tmp_path)
    newer = replace(original, site_city="Neustadt")
    assert service.update_project_profile_if_unchanged("P1", original, newer)
    with pytest.raises(ValueError, match="zwischenzeitlich"):
        service.update_project_profile_if_unchanged(
            "P1", original, replace(original, site_city="Veraltete Daten"),
        )
    assert service.project_profile("P1") == newer


def test_noop_does_not_write_and_legacy_profile_can_be_added(tmp_path):
    service, profile = seeded_service(tmp_path)
    assert service.update_project_profile_if_unchanged("P1", profile, profile) is False
    service.create_project("LEGACY", "Alte Anlage ohne Profil")
    assert service.project_profile("LEGACY") is None
    assert service.update_project_profile_if_unchanged(
        "LEGACY", None, profile,
    ) is True
    assert service.project_profile("LEGACY") == profile
    with pytest.raises(ValueError, match="zwischenzeitlich"):
        service.update_project_profile_if_unchanged(
            "LEGACY", None, replace(profile, inspector="Nicht erlaubt"),
        )


def test_unknown_project_and_invalid_profiles_fail_without_mutation(tmp_path):
    service, profile = seeded_service(tmp_path)
    for bad in (None, "not a profile", {}, 42):
        with pytest.raises(TypeError):
            service.update_project_profile_if_unchanged("P1", profile, bad)
    with pytest.raises(TypeError):
        service.update_project_profile_if_unchanged("P1", "wrong expected", profile)
    with pytest.raises(KeyError, match="Unknown project"):
        service.update_project_profile_if_unchanged("MISSING", None, profile)
    with pytest.raises(ValueError):
        replace(profile, site_timezone="Not/A-Real-Timezone")
    assert service.project_profile("P1") == profile


def test_stale_snapshot_rejected_even_when_other_fields_only_change(tmp_path):
    service, original = seeded_service(tmp_path)
    changed = replace(original, customer_contact="Neuer Ansprechpartner")
    assert service.update_project_profile_if_unchanged("P1", original, changed)
    with pytest.raises(ValueError, match="zwischenzeitlich"):
        service.update_project_profile_if_unchanged(
            "P1", original, replace(original, inspector="Fachperson B"),
        )
    assert service.project_profile("P1") == changed
