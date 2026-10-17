"""Create a local, non-metric visual RGB preview from two DJI frames."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
from zipfile import ZipFile

import cv2
import numpy as np

from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip
from mcm_solarcheck.services.visual_pair_mosaic import compose_visual_pair

_PATTERN = re.compile(r"DJI_\d{14}_(\d{4})_V\.JPG", re.IGNORECASE)


def preview_rgb_pair(archive_path, first_id, second_id, output_path, *, max_image_bytes=80_000_000, max_side=800):
    """Use only local ZIP bytes; never write source frames or EXIF metadata."""
    if not (re.fullmatch(r"\d{4}", first_id) and re.fullmatch(r"\d{4}", second_id)) or first_id == second_id:
        raise ValueError("two distinct four-digit DJI frame IDs required")
    if type(max_image_bytes) is not int or max_image_bytes <= 0 or type(max_side) is not int or max_side < 128:
        raise ValueError("invalid resource limits")
    inspect_dji_flight_zip(archive_path)
    selected = {}
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            match = _PATTERN.fullmatch(Path(member.filename).name)
            if not match or match.group(1) not in (first_id, second_id):
                continue
            if match.group(1) in selected:
                raise ValueError("duplicate RGB frame ID")
            if member.file_size > max_image_bytes:
                raise ValueError("RGB frame exceeds size limit")
            with archive.open(member) as stream:
                payload = stream.read(max_image_bytes + 1)
            if len(payload) > max_image_bytes:
                raise ValueError("RGB frame exceeds size limit")
            frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("unreadable RGB JPEG")
            h, w = frame.shape[:2]
            scale = min(1., max_side / max(h, w))
            if scale < 1:
                frame = cv2.resize(frame, (round(w * scale), round(h * scale)))
            selected[match.group(1)] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if set(selected) != {first_id, second_id}:
        raise ValueError("requested RGB frame ID missing")
    result = compose_visual_pair(selected[first_id], selected[second_id])
    destination = Path(output_path)
    if destination.suffix.lower() != ".png":
        raise ValueError("output must be a local PNG")
    if destination.exists():
        raise ValueError("refusing to overwrite existing preview")
    if not destination.parent.is_dir():
        raise ValueError("output directory does not exist")
    ok, encoded = cv2.imencode(".png", cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("could not encode preview")
    with destination.open("xb") as stream:
        stream.write(encoded.tobytes())
    return result.inliers


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline NON-METRIC visual RGB pair preview")
    parser.add_argument("archive")
    parser.add_argument("first_id")
    parser.add_argument("second_id")
    parser.add_argument("output_png")
    args = parser.parse_args(argv)
    try:
        inliers = preview_rgb_pair(args.archive, args.first_id, args.second_id, args.output_png)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Visual preview failed: {exc}\n")
    print(f"NON-METRIC RGB preview written; RANSAC inliers: {inliers}; NOT an orthophoto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
