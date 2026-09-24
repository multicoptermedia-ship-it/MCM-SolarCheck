"""Backend adapter for reviewed detection geometry in YOLO label format."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path


def _validated_class_ids(class_ids: dict[str,int]) -> dict[str,int]:
    if not isinstance(class_ids,dict) or not class_ids:
        raise ValueError("YOLO class map must be a non-empty dictionary")
    normalized={}
    for name,class_id in class_ids.items():
        if not isinstance(name,str) or not name.strip():
            raise ValueError("YOLO class names must be non-empty strings")
        if not isinstance(class_id,int) or isinstance(class_id,bool) or class_id < 0:
            raise ValueError("YOLO class id must be a non-negative integer")
        normalized[name]=class_id
    ids=sorted(normalized.values())
    if len(ids)!=len(set(ids)):
        raise ValueError("YOLO class ids must be unique")
    if ids!=list(range(len(ids))):
        raise ValueError("YOLO class ids must be contiguous from zero")
    return normalized


def yolo_detection_line(defect_class: str, class_ids: dict[str,int], box_xyxy, width: int, height: int) -> str:
    class_ids=_validated_class_ids(class_ids)
    if defect_class not in class_ids:
        raise ValueError(f"defect class has no YOLO class id: {defect_class}")
    if not isinstance(width,int) or isinstance(width,bool) or width <= 0 or not isinstance(height,int) or isinstance(height,bool) or height <= 0:
        raise ValueError("YOLO source dimensions must be positive integers")
    if box_xyxy is None or len(box_xyxy)!=4:
        raise ValueError("YOLO detection export requires a reviewed box")
    x1,y1,x2,y2=(float(v) for v in box_xyxy)
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1 or x2 > width or y2 > height:
        raise ValueError("YOLO detection box lies outside source image bounds")
    cx=((x1+x2)/2)/width; cy=((y1+y2)/2)/height
    bw=(x2-x1)/width; bh=(y2-y1)/height
    return f"{class_ids[defect_class]} {cx:.10f} {cy:.10f} {bw:.10f} {bh:.10f}"


def _occurrence_key(row: dict) -> str:
    return f'{row["modality"]}:{row["source_frame_id"]}'


def _label_filename(occurrence_key: str) -> str:
    return sha256(occurrence_key.encode("utf-8")).hexdigest()+".txt"


def build_yolo_detection_manifest(snapshot, class_ids: dict[str,int], dimensions: dict[str,tuple[int,int]]) -> dict:
    """Build a deterministic multi-object YOLO manifest per source-frame occurrence."""
    from .training_export import build_spatial_training_index
    class_ids=_validated_class_ids(class_ids)
    grouped={}
    for row in build_spatial_training_index(snapshot,"detection"):
        sample_id=row["sample_id"]
        occurrence=_occurrence_key(row)
        dimension_key=occurrence if occurrence in dimensions else sample_id
        if dimension_key not in dimensions:
            raise ValueError(f"missing source dimensions for YOLO sample: {occurrence}")
        width,height=dimensions[dimension_key]
        label=yolo_detection_line(row["defect_class"],class_ids,row["box_xyxy"],width,height)
        provenance=(row["source_file"],row["content_sha256"],row["modality"],row["representation"],row["split"])
        current=grouped.get(occurrence)
        if current is None:
            grouped[occurrence]={
                "occurrence_key":occurrence,
                "sample_id":sample_id,
                "source_frame_id":row["source_frame_id"],
                "source_file":row["source_file"],
                "content_sha256":row["content_sha256"],
                "modality":row["modality"],
                "representation":row["representation"],
                "split":row["split"],
                "label_file":_label_filename(occurrence),
                "labels":[label],
            }
        else:
            expected=(current["source_file"],current["content_sha256"],current["modality"],current["representation"],current["split"])
            if provenance!=expected or sample_id!=current["sample_id"]:
                raise ValueError("inconsistent provenance for YOLO source-frame occurrence")
            current["labels"].append(label)
    rows=list(grouped.values())
    for row in rows:
        row["labels"]=sorted(set(row["labels"]))
    rows.sort(key=lambda x:(x["split"],x["occurrence_key"]))
    return {"task":"detection","format":"yolo","class_ids":dict(sorted(class_ids.items())),"rows":rows}


def write_yolo_detection_dataset(manifest: dict, destination) -> None:
    """Preflight all content, then write deterministic labels and split lists."""
    root=Path(destination)
    rows=manifest["rows"]
    encoded=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    planned={}
    for row in rows:
        source=Path(row["source_file"])
        if not source.is_file():
            raise FileNotFoundError(f"YOLO source is unavailable: {source}")
        if sha256(source.read_bytes()).hexdigest()!=row["content_sha256"]:
            raise ValueError(f"YOLO source SHA-256 changed: {source}")
        label_file=row["label_file"]
        if Path(label_file).name!=label_file:
            raise ValueError("YOLO label filename must not contain a path")
        planned[Path("labels")/label_file]="".join(line+chr(10) for line in row["labels"])
    for split in ("train","validation","test"):
        split_rows=[r for r in rows if r["split"]==split]
        planned[Path(f"{split}.txt")]="".join(str(r["source_file"])+chr(10) for r in split_rows)
    planned[Path("manifest.json")]=encoded
    for relative,content in planned.items():
        target=root/relative
        if target.exists() and target.read_text(encoding="utf-8")!=content:
            raise FileExistsError(f"refusing to overwrite different YOLO dataset content: {target}")
    root.mkdir(parents=True,exist_ok=True)
    (root/"labels").mkdir(exist_ok=True)
    for relative,content in planned.items():
        (root/relative).write_text(content,encoding="utf-8")
