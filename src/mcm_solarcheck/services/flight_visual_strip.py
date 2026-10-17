"""Offline CLI for short non-metric DJI RGB strip previews."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
from zipfile import ZipFile

import cv2
import numpy as np

from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip
from mcm_solarcheck.services.visual_strip_preview import compose_visual_strip

_PATTERN = re.compile(r"DJI_\d{14}_(\d{4})_V\.JPG", re.IGNORECASE)


def preview_rgb_strip(archive_path, frame_ids, output_path, *, max_image_bytes=80_000_000, max_side=800):
    ids = tuple(frame_ids)
    if not 2 <= len(ids) <= 4 or len(set(ids)) != len(ids) or any(not re.fullmatch(r"\d{4}", i) for i in ids):
        raise ValueError("provide 2-4 distinct four-digit RGB frame IDs")
    if type(max_image_bytes) is not int or max_image_bytes <= 0 or type(max_side) is not int or max_side < 128:
        raise ValueError("invalid resource limits")
    inspect_dji_flight_zip(archive_path)
    frames = {}
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            match = _PATTERN.fullmatch(Path(member.filename).name)
            if not match or match.group(1) not in ids:
                continue
            frame_id = match.group(1)
            if frame_id in frames or member.file_size > max_image_bytes:
                raise ValueError("duplicate or oversized RGB frame")
            with archive.open(member) as stream:
                data = stream.read(max_image_bytes + 1)
            if len(data) > max_image_bytes:
                raise ValueError("oversized RGB frame")
            decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if decoded is None:
                raise ValueError("unreadable RGB frame")
            h, w = decoded.shape[:2]
            scale = min(1., max_side / max(h, w))
            if scale < 1:
                decoded = cv2.resize(decoded, (max(1, round(w * scale)), max(1, round(h * scale))))
            frames[frame_id] = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
    if set(frames) != set(ids):
        raise ValueError("one or more requested RGB frames are missing")
    result = compose_visual_strip([frames[i] for i in ids])
    destination = Path(output_path)
    if destination.suffix.lower() != ".png" or not destination.parent.is_dir() or destination.exists():
        raise ValueError("output must be a new PNG in an existing local directory")
    ok, png = cv2.imencode(".png", cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("PNG encoding failed")
    with destination.open("xb") as stream:
        stream.write(png.tobytes())
    return result.pair_inliers


def main(argv=None):
    parser = argparse.ArgumentParser(description="NON-METRIC offline RGB visual strip (2-4 frames)")
    parser.add_argument("archive")
    parser.add_argument("output_png")
    parser.add_argument("frame_ids", nargs="+")
    args = parser.parse_args(argv)
    try:
        counts = preview_rgb_strip(args.archive, args.frame_ids, args.output_png)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Visual strip failed: {exc}\n")
    print(f"NON-METRIC visual strip, NOT an orthophoto; RANSAC inliers per stage: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
