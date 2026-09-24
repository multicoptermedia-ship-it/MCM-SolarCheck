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
        group_id=label.get("inspection_group_id") or label["module_id"] or label["finding_id"]
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
            "inspection_group_id":label.get("inspection_group_id"),
            "defect_class":label["defect_class"],
            "split":split,
        })
    assert_no_group_leakage(assignments)
    return tuple(rows)


def build_spatial_training_index(snapshot, task: str) -> tuple[dict, ...]:
    """Export only labels with reviewed geometry suitable for a spatial task."""
    if task not in {"detection","segmentation"}:
        raise ValueError("spatial training task must be detection or segmentation")
    manifest=json.loads(snapshot.manifest_json)
    geometries={g["label_id"]:g for g in manifest.get("geometries",())}
    rows=[]
    for row,label in zip(build_training_index(snapshot),manifest["labels"]):
        geometry=geometries.get(label["label_id"])
        if geometry is None:
            raise ValueError("spatial training label has no reviewed geometry")
        if task=="detection" and geometry.get("box_xyxy") is None:
            raise ValueError("detection label has no reviewed bounding box")
        if task=="segmentation" and geometry.get("polygon_px") is None:
            raise ValueError("segmentation label has no reviewed polygon")
        rows.append({**row,"representation":geometry["representation"],"box_xyxy":geometry.get("box_xyxy"),"polygon_px":geometry.get("polygon_px")})
    return tuple(rows)
