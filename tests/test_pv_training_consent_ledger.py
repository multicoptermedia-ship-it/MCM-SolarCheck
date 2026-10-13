import pytest
from PIL import Image

from mcm_solarcheck.services.pv_training_consent_ledger import TrainingConsentLedger
from mcm_solarcheck.services.pv_module_training_crop import ModuleCropReview
from mcm_solarcheck.services.pv_consented_module_export import export_with_active_consent


def test_opt_in_revocation_and_regrant(tmp_path):
    ledger = TrainingConsentLedger(tmp_path / "consent.sqlite")
    assert not ledger.current("project").active
    with pytest.raises(PermissionError):
        ledger.grant("project")
    first = ledger.grant("project", affirmative_opt_in=True)
    ledger.require_active("project", first)
    ledger.revoke("project")
    with pytest.raises(PermissionError):
        ledger.require_active("project", first)
    second = ledger.grant("project", affirmative_opt_in=True)
    assert second != first
    with pytest.raises(PermissionError):
        ledger.require_active("project", first)
    ledger.require_active("project", second)


def test_export_requires_current_consent(tmp_path):
    ledger = TrainingConsentLedger(tmp_path / "consent.sqlite")
    source = tmp_path / "source.png"
    Image.new("RGB", (128, 128)).save(source)
    ref = ledger.grant("project", affirmative_opt_in=True)
    review = ModuleCropReview(ref, "reviewer", True, True, (0, 0, 1, 1))
    ledger.revoke("project")
    with pytest.raises(PermissionError):
        export_with_active_consent(source, tmp_path, review, "project", ledger)
    new_ref = ledger.grant("project", affirmative_opt_in=True)
    new_review = ModuleCropReview(new_ref, "reviewer", True, True, (0, 0, 1, 1))
    result = export_with_active_consent(source, tmp_path, new_review, "project", ledger)
    assert result.output_path.exists()
