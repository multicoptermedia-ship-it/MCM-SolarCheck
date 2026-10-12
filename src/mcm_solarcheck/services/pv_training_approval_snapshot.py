"""Bind an audited dataset, site manifest and reviewed training plan to one digest."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from mcm_solarcheck.services.pv_dataset_intake import PublicDatasetRecord
from mcm_solarcheck.services.pv_training_dataset_fingerprint import fingerprint_local_yolo_dataset
from mcm_solarcheck.services.pv_yolo_class_mapping import YoloClassMapping
from mcm_solarcheck.services.pv_yolo_dataset_audit import audit_local_yolo_dataset
from mcm_solarcheck.services.pv_yolo_training_plan import YoloTrainingPlan, prepare_yolo_training_plan


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TrainingApprovalSnapshot:
    dataset_sha256: str
    group_manifest_sha256: str
    approval_sha256: str
    plan: YoloTrainingPlan
    status: str = "approved_metadata_only"


def prepare_training_approval_snapshot(
    root: Path, record: PublicDatasetRecord, mapping: YoloClassMapping,
    site_by_image: dict[str, str], *, model_reference: str,
    weights_license_review_reference: str, seed: int = 42,
    epochs: int = 50, image_size: int = 640, batch_size: int = 8,
) -> TrainingApprovalSnapshot:
    """Rehash around the audit to reject observed in-process dataset changes."""
    before = fingerprint_local_yolo_dataset(root)
    groups_before = _digest(site_by_image)
    audit = audit_local_yolo_dataset(root, record, mapping, site_by_image)
    after = fingerprint_local_yolo_dataset(root)
    if before != after or groups_before != _digest(site_by_image):
        raise ValueError("dataset or group manifest changed during approval")
    plan = prepare_yolo_training_plan(
        record, mapping, audit, after, model_reference=model_reference,
        weights_license_review_reference=weights_license_review_reference,
        seed=seed, epochs=epochs, image_size=image_size, batch_size=batch_size,
    )
    evidence = {
        "dataset": after.digest_sha256, "groups": groups_before,
        "record": {
            "id": record.dataset_id, "source": record.source_url,
            "modality": record.modality.value, "license": record.license_name,
            "decision": record.decision.value, "reviewer": record.reviewer,
            "evidence": record.evidence_reference,
        },
        "mapping": {
            "external": mapping.external_names,
            "observations": [item.value if item is not None else None
                             for item in mapping.mapped_observations],
        },
        "plan": asdict(plan),
    }
    return TrainingApprovalSnapshot(after.digest_sha256, groups_before,
                                    _digest(evidence), plan)


def verify_training_approval_snapshot(
    root: Path, site_by_image: dict[str, str],
    snapshot: TrainingApprovalSnapshot,
) -> bool:
    """Recheck current local files and group manifest; never starts training."""
    if not isinstance(snapshot, TrainingApprovalSnapshot):
        raise TypeError("training approval snapshot required")
    current = fingerprint_local_yolo_dataset(root)
    return (current.digest_sha256 == snapshot.dataset_sha256
            and _digest(site_by_image) == snapshot.group_manifest_sha256
            and snapshot.plan.dataset_sha256 == snapshot.dataset_sha256)
