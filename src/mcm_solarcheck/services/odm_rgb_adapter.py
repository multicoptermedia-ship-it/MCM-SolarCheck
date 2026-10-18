"""Prepare a read-only DJI RGB image list for an external ODM runner.

This adapter never invokes Docker, modifies originals, or claims an orthophoto.
"""
from pathlib import Path
from mcm_solarcheck.services.flight_inventory import scan_flight


def prepare_odm_rgb_inputs(folder, *, max_captures=1000):
    if type(max_captures) is not int or max_captures < 1:
        raise ValueError("invalid capture limit")
    captures, ignored = scan_flight(folder)
    if len(captures) > max_captures:
        raise ValueError("flight exceeds configured capture limit")
    rgb = tuple(path for _, path, _ in captures if path is not None)
    missing = tuple(key for key, path, _ in captures if path is None)
    if not rgb:
        raise ValueError("flight contains no RGB images")
    return {"rgb": rgb, "missing_rgb": missing,
            "capture_count": len(captures), "ignored": ignored}
