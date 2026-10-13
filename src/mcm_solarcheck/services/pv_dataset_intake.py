"""Fail-closed provenance and license intake for public PV training datasets."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class ImageModality(str, Enum):
    RGB = "rgb"
    THERMAL = "thermal"
    EL = "electroluminescence"


class LicenseDecision(str, Enum):
    UNREVIEWED = "unreviewed"
    APPROVED_COMMERCIAL = "approved_commercial"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PublicDatasetRecord:
    dataset_id: str
    source_url: str
    modality: ImageModality
    license_name: str
    decision: LicenseDecision = LicenseDecision.UNREVIEWED
    reviewer: str | None = None
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.license_name.strip():
            raise ValueError("dataset identifier and license declaration required")
        url = urlparse(self.source_url)
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError("HTTPS provenance URL required")
        if not isinstance(self.modality, ImageModality) or not isinstance(self.decision, LicenseDecision):
            raise ValueError("recognized modality and license decision required")
        if self.decision is LicenseDecision.APPROVED_COMMERCIAL:
            if not self.reviewer or not self.reviewer.strip() or not self.evidence_reference or not self.evidence_reference.strip():
                raise ValueError("commercial approval requires human reviewer and evidence")
            if "nc" in self.license_name.lower().replace("-", "").replace(" ", ""):
                raise ValueError("noncommercial dataset cannot be commercially approved")

    def can_train_commercially(self, expected_modality: ImageModality) -> bool:
        return self.decision is LicenseDecision.APPROVED_COMMERCIAL and self.modality is expected_modality
