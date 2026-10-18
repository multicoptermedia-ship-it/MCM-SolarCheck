"""Inspect every recognized DJI image independently, without discarding failures."""
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np

from mcm_solarcheck.services.flight_inventory import scan_flight


def inspect_flight_images(folder, *, max_image_bytes=80_000_000):
    """Return one status per recognized RGB/thermal file, including failures.

    Thermal decoding checks readability only; no radiometric temperature claim.
    """
    if type(max_image_bytes) is not int or max_image_bytes <= 0:
        raise ValueError("invalid image byte limit")
    captures, ignored = scan_flight(folder)
    statuses = []
    for key, rgb, thermal in captures:
        for modality, path in (("rgb", rgb), ("thermal", thermal)):
            if path is None:
                statuses.append({"capture": key, "modality": modality,
                                 "status": "missing", "filename": None})
                continue
            status = "readable"
            width = height = None
            try:
                if path.stat().st_size > max_image_bytes:
                    status = "oversized"
                else:
                    raw = path.read_bytes()
                    if len(raw) > max_image_bytes:
                        status = "oversized"
                    else:
                        decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8),
                                              cv2.IMREAD_UNCHANGED)
                        if decoded is None:
                            status = "unreadable"
                        else:
                            height, width = decoded.shape[:2]
            except OSError:
                status = "unreadable"
            statuses.append({"capture": key, "modality": modality,
                             "status": status, "filename": path.name,
                             "width": width, "height": height})
    return {"captures": len(captures), "images": statuses,
            "ignored": list(ignored),
            "readable": sum(item["status"] == "readable" for item in statuses),
            "unreadable": sum(item["status"] == "unreadable" for item in statuses),
            "oversized": sum(item["status"] == "oversized" for item in statuses),
            "missing": sum(item["status"] == "missing" for item in statuses)}
