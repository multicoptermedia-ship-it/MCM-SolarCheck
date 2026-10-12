"""Consent-gated export of a reviewed module image."""
from pathlib import Path

from mcm_solarcheck.services.pv_module_training_crop import (
    ModuleCropReview, export_reviewed_rgb_module_crop,
)
from mcm_solarcheck.services.pv_training_consent_ledger import TrainingConsentLedger


def export_with_active_consent(
    source: Path, destination: Path, review: ModuleCropReview,
    project_key: str, ledger: TrainingConsentLedger,
):
    ledger.require_active(project_key, review.consent_reference)
    return export_reviewed_rgb_module_crop(source, destination, review)
