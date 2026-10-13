"""Fail-closed deterministic metadata plan; deliberately does not run YOLO."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_dataset_intake import PublicDatasetRecord
from mcm_solarcheck.services.pv_training_dataset_fingerprint import DatasetFingerprint
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping
from mcm_solarcheck.services.pv_yolo_dataset_audit import DatasetAudit


@dataclass(frozen=True)
class YoloTrainingPlan:
    dataset_sha256: str
    dataset_id: str
    modality: str
    classes: tuple[str, ...]
    seed: int
    epochs: int
    image_size: int
    batch_size: int
    model_reference: str
    weights_license_review_reference: str
    status: str = "plan_only_no_training"


def prepare_yolo_training_plan(
    record: PublicDatasetRecord, mapping: YoloClassMapping,
    audit: DatasetAudit, fingerprint: DatasetFingerprint, *,
    seed: int = 42, epochs: int = 50, image_size: int = 640,
    batch_size: int = 8, model_reference: str,
    weights_license_review_reference: str,
) -> YoloTrainingPlan:
    if not isinstance(record, PublicDatasetRecord) or not isinstance(mapping, YoloClassMapping):
        raise TypeError("validated record and mapping required")
    if not isinstance(audit, DatasetAudit) or audit.training_ready is not True:
        raise PermissionError("dataset audit has not passed")
    if not record.can_train_commercially(mapping.modality):
        raise PermissionError("human-reviewed commercial dataset license required")
    if not isinstance(fingerprint, DatasetFingerprint) or fingerprint.file_count < 6 or len(fingerprint.digest_sha256) != 64:
        raise ValueError("complete dataset fingerprint required")
    if any(item is None for item in mapping.mapped_observations):
        raise ValueError("unmapped training class")
    if (type(seed) is not int or seed < 0 or type(epochs) is not int or not 1 <= epochs <= 1000
            or type(image_size) is not int or not 32 <= image_size <= 4096
            or type(batch_size) is not int or not 1 <= batch_size <= 256):
        raise ValueError("invalid bounded training hyperparameters")
    if not isinstance(model_reference, str) or not model_reference.strip():
        raise ValueError("explicit model reference required")
    if not isinstance(weights_license_review_reference, str) or not weights_license_review_reference.strip():
        raise ValueError("weights license review required")
    return YoloTrainingPlan(
        fingerprint.digest_sha256, record.dataset_id, mapping.modality.value,
        tuple(item.value for item in mapping.mapped_observations if item is not None),
        seed, epochs, image_size, batch_size,
        model_reference, weights_license_review_reference,
    )
