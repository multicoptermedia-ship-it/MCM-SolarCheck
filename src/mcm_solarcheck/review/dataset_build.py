"""Integrity-checked, reproducible dataset build contract."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json

from .training_export import build_training_index


@dataclass(frozen=True)
class DatasetBuild:
    snapshot_id: str
    dataset_id: str
    sample_count: int
    class_counts: dict[str, int]
    split_counts: dict[str, int]
    manifest_json: str


def _verify_row(row: dict) -> None:
    path=Path(row["source_file"])
    if not path.is_file():
        raise FileNotFoundError(f"training source is unavailable: {path}")
    digest=sha256(path.read_bytes()).hexdigest()
    if digest != row["content_sha256"]:
        raise ValueError(f"training source SHA-256 changed: {path}")


def build_dataset(snapshot) -> DatasetBuild:
    rows=build_training_index(snapshot)
    if not rows:raise ValueError("training dataset must contain at least one reviewed, rights-approved sample")
    for row in rows:
        if row["defect_class"]=="unknown":raise ValueError("unknown ground truth cannot enter a training dataset")
        _verify_row(row)
    manifest={
        "snapshot_id":snapshot.snapshot_id,
        "split_policy":{"strategy":"inspection_or_physical_group_sha256","train":80,"validation":10,"test":10},
        "rows":rows,
    }
    encoded=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return DatasetBuild(
        snapshot_id=snapshot.snapshot_id,
        dataset_id=sha256(encoded.encode()).hexdigest(),
        sample_count=len(rows),
        class_counts=dict(sorted(Counter(r["defect_class"] for r in rows).items())),
        split_counts=dict(sorted(Counter(r["split"] for r in rows).items())),
        manifest_json=encoded,
    )
