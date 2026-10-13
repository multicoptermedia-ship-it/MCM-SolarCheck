"""Public thermal dataset candidate registry; never grants commercial permission."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_dataset_intake import ImageModality, LicenseDecision, PublicDatasetRecord


@dataclass(frozen=True)
class ThermalDatasetCandidate:
    dataset_id: str
    source_url: str
    advertised_license: str
    advertised_image_count: int
    rights_checklist: tuple[str, ...]
    status: str = "candidate_unreviewed"

    def to_unreviewed_record(self) -> PublicDatasetRecord:
        return PublicDatasetRecord(
            self.dataset_id, self.source_url, ImageModality.THERMAL,
            self.advertised_license, LicenseDecision.UNREVIEWED,
        )


THERMAL_CANDIDATES = (
    ThermalDatasetCandidate(
        "roboflow_solar_hotspot",
        "https://universe.roboflow.com/thermal-images-of-solar-panels/solar-hotspot-gu8ap",
        "MIT (provider claim; original image rights unverified)",
        2113,
        ("original photographer rights", "derivative redistribution permission",
         "commercial use", "annotations provenance", "site-disjoint validation",
         "negative samples", "license evidence archived"),
    ),
)


def require_reviewed_thermal_dataset(record: PublicDatasetRecord) -> None:
    if not isinstance(record, PublicDatasetRecord) or not record.can_train_commercially(ImageModality.THERMAL):
        raise PermissionError("thermal training dataset requires documented commercial approval")
