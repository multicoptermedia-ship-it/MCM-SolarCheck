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
    labels=database.ground_truth(project_id)\n    geometries=database.training_geometries(project_id) if hasattr(database,"training_geometries") else ()
    trainable_frames={s["source_frame_id"] for s in samples}
    latest={}
    for label in labels:
        if label["source_frame_id"] in trainable_frames:
            key=(label["source_frame_id"],label["module_id"],label["finding_id"])
            latest[key]=label
    manifest={
        "project_id":project_id,
        "samples":sorted(samples,key=lambda x:x["sample_id"]),
        "labels":sorted(latest.values(),key=lambda x:(x["source_frame_id"],x["module_id"] or "",x["finding_id"] or "")),\n        "geometries":sorted(geometries,key=lambda x:(x["source_frame_id"],x["label_id"])),
    }
    encoded=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return TrainingSnapshot(sha256(encoded.encode()).hexdigest(),len(samples),len(latest),encoded)


def write_training_snapshot(snapshot: TrainingSnapshot, destination) -> None:
    """Write immutable snapshot manifest, refusing silent replacement."""
    from pathlib import Path
    path=Path(destination)
    if path.exists():
        existing=path.read_text(encoding="utf-8")
        if existing != snapshot.manifest_json:
            raise FileExistsError(f"refusing to overwrite training snapshot: {path}")
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(snapshot.manifest_json,encoding="utf-8")
