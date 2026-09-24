"""Backend adapter for reviewed detection geometry in YOLO label format."""
from __future__ import annotations


def yolo_detection_line(defect_class: str, class_ids: dict[str,int], box_xyxy, width: int, height: int) -> str:
    if defect_class not in class_ids:
        raise ValueError(f"defect class has no YOLO class id: {defect_class}")
    class_id=class_ids[defect_class]
    if not isinstance(class_id,int) or isinstance(class_id,bool) or class_id < 0:
        raise ValueError("YOLO class id must be a non-negative integer")
    if not isinstance(width,int) or isinstance(width,bool) or width <= 0 or not isinstance(height,int) or isinstance(height,bool) or height <= 0:
        raise ValueError("YOLO source dimensions must be positive integers")
    if box_xyxy is None or len(box_xyxy)!=4:
        raise ValueError("YOLO detection export requires a reviewed box")
    x1,y1,x2,y2=(float(v) for v in box_xyxy)
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1 or x2 > width or y2 > height:
        raise ValueError("YOLO detection box lies outside source image bounds")
    cx=((x1+x2)/2)/width; cy=((y1+y2)/2)/height
    bw=(x2-x1)/width; bh=(y2-y1)/height
    return f"{class_id} {cx:.10f} {cy:.10f} {bw:.10f} {bh:.10f}"


def build_yolo_detection_manifest(snapshot, class_ids: dict[str,int], dimensions: dict[str,tuple[int,int]]) -> dict:
    """Build a deterministic YOLO-ready manifest without copying source images."""
    import json
    from .training_export import build_spatial_training_index
    rows=[]
    for row in build_spatial_training_index(snapshot,"detection"):
        sample_id=row["sample_id"]
        if sample_id not in dimensions:
            raise ValueError(f"missing source dimensions for YOLO sample: {sample_id}")
        width,height=dimensions[sample_id]
        label=yolo_detection_line(row["defect_class"],class_ids,row["box_xyxy"],width,height)
        rows.append({
            "sample_id":sample_id,
            "source_file":row["source_file"],
            "content_sha256":row["content_sha256"],
            "modality":row["modality"],
            "representation":row["representation"],
            "split":row["split"],
            "label":label,
        })
    rows.sort(key=lambda x:(x["split"],x["sample_id"],x["label"]))
    return {"task":"detection","format":"yolo","class_ids":dict(sorted(class_ids.items())),"rows":rows}


def write_yolo_detection_dataset(manifest: dict, destination) -> None:
    """Write deterministic labels/split lists; source images remain external and hashed."""
    from pathlib import Path
    import json
    root=Path(destination)
    root.mkdir(parents=True,exist_ok=True)
    rows=manifest["rows"]\n    names=[r["sample_id"].replace(":","_") for r in rows]\n    if len(names)!=len(set(names)):\n        raise ValueError("YOLO label filename collision after sample-id normalization")
    for split in ("train","validation","test"):
        split_rows=[r for r in rows if r["split"]==split]
        (root/f"{split}.txt").write_text("".join(f'{r["source_file"]}\n' for r in split_rows),encoding="utf-8")
    labels=root/"labels"; labels.mkdir(exist_ok=True)
    for row in rows:
        (labels/f'{row["sample_id"].replace(":","_")}.txt').write_text(row["label"]+"\n",encoding="utf-8")
    encoded=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    for row in rows:\n        source=Path(row["source_file"])\n        if not source.is_file():\n            raise FileNotFoundError(f"YOLO source is unavailable: {source}")\n        from hashlib import sha256\n        if sha256(source.read_bytes()).hexdigest()!=row["content_sha256"]:\n            raise ValueError(f"YOLO source SHA-256 changed: {source}")\n    target=root/"manifest.json"
    if target.exists() and target.read_text(encoding="utf-8")!=encoded:
        raise FileExistsError("refusing to overwrite YOLO dataset manifest with different content")
    target.write_text(encoded,encoding="utf-8")
