"""Reproducible snapshots of approved human ground truth."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class TrainingSnapshot:
    snapshot_id: str
    sample_count: int
    label_count: int
    manifest_json: str


def build_training_snapshot(database, project_id: str) -> TrainingSnapshot:
    samples=database.training_samples(project_id,trainable_only=True)
    labels=database.ground_truth(project_id)
    trainable_frames={s["source_frame_id"] for s in samples}
    latest={}
    for label in labels:
        if label["source_frame_id"] in trainable_frames:
            key=(label["source_frame_id"],label["module_id"],label["finding_id"])
            latest[key]=label
    manifest={
        "project_id":project_id,
        "samples":sorted(samples,key=lambda x:x["sample_id"]),
        "labels":sorted(latest.values(),key=lambda x:(x["source_frame_id"],x["module_id"] or "",x["finding_id"] or "")),
    }
    encoded=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return TrainingSnapshot(sha256(encoded.encode()).hexdigest(),len(samples),len(latest),encoded)
