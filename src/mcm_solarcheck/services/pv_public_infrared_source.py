"""Pinned public PV infrared benchmark: source verification, not automatic rights grant."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_dataset_intake import (
    ImageModality, LicenseDecision, PublicDatasetRecord,
)

DATASET_ID = "raptor_maps_infrared_solar_modules"
SOURCE_URL = "https://github.com/RaptorMaps/InfraredSolarModules"
UPSTREAM_COMMIT = "88e2d1febbcefe401c17ec80b8973f36a02a1653"
ARCHIVE_NAME = "2020-02-14_InfraredSolarModules.zip"
ARCHIVE_GIT_BLOB_SHA1 = "2697c73ef1aa58af4dc8aad35ca182ce2586861a"
ARCHIVE_SIZE = 15_495_990
ARCHIVE_URL = (
    "https://raw.githubusercontent.com/RaptorMaps/InfraredSolarModules/"
    + UPSTREAM_COMMIT + "/" + ARCHIVE_NAME
)
LICENSE_URL = (
    "https://github.com/RaptorMaps/InfraredSolarModules/blob/"
    + UPSTREAM_COMMIT + "/LICENSE"
)
ORIGINAL_CLASSES = (
    "Cell", "Cell-Multi", "Cracking", "Hot-Spot", "Hot-Spot-Multi",
    "Shadowing", "Diode", "Diode-Multi", "Vegetation", "Soiling",
    "Offline-Module", "No-Anomaly",
)
MODALITY = "infrared-jpeg-8bit-not-radiometric"
REVIEW_LIMIT = (
    "The upstream labels are image-level anomaly names. No human-reviewed "
    "DJI-Mavic-3T radiometric ground truth, defect geometry or physical-site "
    "group IDs are supplied. Use only in separate exploratory experiments."
)


def unreviewed_license_record() -> PublicDatasetRecord:
    """MIT is a published source claim, NOT a technical/commercial approval."""
    return PublicDatasetRecord(
        DATASET_ID, SOURCE_URL, ImageModality.THERMAL, "MIT",
        LicenseDecision.UNREVIEWED,
    )


@dataclass(frozen=True)
class RaptorImportAuthorization:
    reviewer: str
    evidence_reference: str
    explicit_exploratory_only: bool

    def __post_init__(self) -> None:
        if (not isinstance(self.reviewer, str) or not self.reviewer.strip()
                or len(self.reviewer) > 120
                or not isinstance(self.evidence_reference, str)
                or len(self.evidence_reference.strip()) < 4
                or len(self.evidence_reference) > 300
                or self.explicit_exploratory_only is not True):
            raise PermissionError(
                "explicit local exploratory approval and upstream rights evidence required"
            )

    def reviewed_record(self) -> PublicDatasetRecord:
        return PublicDatasetRecord(
            DATASET_ID, SOURCE_URL, ImageModality.THERMAL,
            "MIT", LicenseDecision.APPROVED_COMMERCIAL,
            self.reviewer, self.evidence_reference,
        )
