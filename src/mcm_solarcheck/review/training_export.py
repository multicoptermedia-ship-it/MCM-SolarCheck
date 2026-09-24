"""Export a reviewed snapshot into a backend-neutral training index."""
from __future__ import annotations
import json
from .training_split import split_for_group, assert_no_group_leakage


def build_training_index(snapshot) -> tuple[dict, ...]:
    manifest=json.loads(snapshot.manifest_json)
    samples={s["source_frame_id"]:s for s in manifest["samples"]}
    rows=[]
    assignments=[]
    for label in manifest["labels"]:
        sample=samples.get(label["source_frame_id"])
        if sample is None:
            raise ValueError("ground truth references sample outside snapshot")
        group_id=label["module_id"] or label["finding_id"]
        if not group_id:
            raise ValueError("training label has no leakage group")
        split=split_for_group(group_id)
        assignments.append((group_id,split))
        rows.append({
            "sample_id":sample["sample_id"],
            "source_file":sample["source_file"],
            "modality":sample["modality"],
            "content_sha256":sample["content_sha256"],
            "module_id":label["module_id"],
            "finding_id":label["finding_id"],
            "defect_class":label["defect_class"],
            "split":split,
        })
    assert_no_group_leakage(assignments)
    return tuple(rows)
