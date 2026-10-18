"""Run bounded RGB registration checks over every capture in a flight.

Each adjacent pair is evaluated once; failed links remain visible.
No image mosaics, metric geometry or thermal temperature claims.
"""
from pathlib import Path
import cv2
import numpy as np

from mcm_solarcheck.services.flight_batch_plan import plan_flight_batches
from mcm_solarcheck.services.visual_frame_registration import estimate_visual_link


def check_flight_rgb_links(folder, *, batch_size=80, overlap=10,
                           max_captures=1000, max_image_bytes=80_000_000,
                           max_side=800):
    if (type(max_side) is not int or max_side < 128 or
            type(max_image_bytes) is not int or max_image_bytes < 1):
        raise ValueError("invalid working preview size")
    plan = plan_flight_batches(folder, batch_size=batch_size, overlap=overlap,
                               max_captures=max_captures)
    captures = []
    seen = set()
    for batch in plan["batches"]:
        for item in batch["captures"]:
            if item[0] not in seen:
                captures.append(item)
                seen.add(item[0])
    def load(path):
        if path is None:
            raise ValueError("RGB image missing")
        if path.is_symlink() or not path.is_file():
            raise ValueError("RGB image not a regular file")
        if path.stat().st_size > max_image_bytes:
            raise ValueError("RGB image exceeds byte limit")
        data = path.read_bytes()
        if len(data) > max_image_bytes:
            raise ValueError("RGB image exceeds byte limit")
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("RGB image unreadable")
        h, w = frame.shape[:2]
        scale = min(1., max_side / max(h, w))
        if scale < 1:
            frame = cv2.resize(frame, (max(1, round(w*scale)), max(1, round(h*scale))))
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    links = []
    for first, second in zip(captures, captures[1:]):
        record = {"first": first[0], "second": second[0], "status": "failed"}
        try:
            _, inliers = estimate_visual_link(load(first[1]), load(second[1]))
            record.update(status="registered", inliers=inliers)
        except (ValueError, OSError, cv2.error) as exc:
            record["reason"] = str(exc)
        links.append(record)
    return {"capture_count": len(captures), "batch_count": len(plan["batches"]),
            "links": links, "registered": sum(x["status"] == "registered" for x in links),
            "failed": sum(x["status"] == "failed" for x in links),
            "metric_orthophoto_verified": False, "temperature_calibrated": False}


def save_flight_rgb_link_run(folder, destination, **options):
    """Persist link-by-link success/failure locally without overwriting files."""
    import json

    target = Path(destination)
    if target.suffix.lower() != ".json" or target.exists() or not target.parent.is_dir():
        raise ValueError("new JSON output path required")
    result = check_flight_rgb_links(folder, **options)
    result["schema_version"] = 1
    result["processing_kind"] = "nonmetric_rgb_link_registration"
    result["full_resolution_sources_modified"] = False
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return result
