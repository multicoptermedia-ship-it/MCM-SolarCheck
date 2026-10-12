"""Explicit pre-run revalidation of local training approval metadata."""
from __future__ import annotations

from pathlib import Path

from mcm_solarcheck.services.pv_dataset_intake import PublicDatasetRecord
from mcm_solarcheck.services.pv_training_approval_snapshot import (
    TrainingApprovalSnapshot, prepare_training_approval_snapshot,
    verify_training_approval_snapshot,
)
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping


def require_matching_training_approval(
    root: Path, record: PublicDatasetRecord, mapping: YoloClassMapping,
    site_by_image: dict[str, str], snapshot: TrainingApprovalSnapshot,
) -> None:
    """Fail closed when any content, approval, mapping or configuration differs."""
    if not isinstance(snapshot, TrainingApprovalSnapshot):
        raise PermissionError("missing approval snapshot")
    if not verify_training_approval_snapshot(root, site_by_image, snapshot):
        raise PermissionError("dataset or group manifest no longer matches approval")
    try:
        current = prepare_training_approval_snapshot(
            root, record, mapping, site_by_image,
            model_reference=snapshot.plan.model_reference,
            weights_license_review_reference=snapshot.plan.weights_license_review_reference,
            seed=snapshot.plan.seed, epochs=snapshot.plan.epochs,
            image_size=snapshot.plan.image_size, batch_size=snapshot.plan.batch_size,
        )
    except (ValueError, TypeError, PermissionError) as exc:
        raise PermissionError("current dataset approval failed") from exc
    if current != snapshot:
        raise PermissionError("approval evidence, class mapping or training plan changed")
