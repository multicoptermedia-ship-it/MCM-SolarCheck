"""Verify a staged local YOLO dataset immediately before controlled consumption."""
from __future__ import annotations

from mcm_solarcheck.services.pv_training_dataset_fingerprint import fingerprint_local_yolo_dataset
from mcm_solarcheck.services.pv_training_local_staging import LocalTrainingStage
from mcm_solarcheck.services.pv_training_approval_snapshot import TrainingApprovalSnapshot


def require_verified_local_training_stage(
    stage: LocalTrainingStage, approval: TrainingApprovalSnapshot,
) -> None:
    """No training is started; caller must additionally enforce an immutable mount."""
    if not isinstance(stage, LocalTrainingStage) or not isinstance(approval, TrainingApprovalSnapshot):
        raise PermissionError("stage and approval required")
    if stage.status != "staged_no_training" or stage.dataset_sha256 != approval.dataset_sha256:
        raise PermissionError("staged dataset does not match approval")
    current = fingerprint_local_yolo_dataset(stage.directory)
    if (current.digest_sha256 != approval.dataset_sha256
            or current.file_count != stage.file_count
            or current.total_bytes != stage.total_bytes):
        raise PermissionError("staged dataset has changed")
