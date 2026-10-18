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
from mcm_solarcheck.services.visual_anchored_preview import compose_anchored_visual_preview
from mcm_solarcheck.services.visual_loop_audit import audit_visual_loops
from mcm_solarcheck.services.visual_projective_preview import compose_projective_visual_preview
from mcm_solarcheck.services.visual_quality_export import projective_quality_json

_PATTERN = re.compile(r"DJI_\d{14}_(\d{4})_V\.JPG", re.IGNORECASE)


def preview_rgb_strip(archive_path, frame_ids, output_path, *, max_image_bytes=80_000_000, max_side=800, anchored=False, audit_loops=False, projective=False, quality_json_path=None):
    ids = tuple(frame_ids)
    if not 2 <= len(ids) <= 4 or len(set(ids)) != len(ids) or any(not re.fullmatch(r"\d{4}", i) for i in ids):
        raise ValueError("provide 2-4 distinct four-digit RGB frame IDs")
    if type(max_image_bytes) is not int or max_image_bytes <= 0 or type(max_side) is not int or max_side < 128:
        raise ValueError("invalid resource limits")
    if quality_json_path is not None and not projective:
        raise ValueError('quality JSON requires --projective')
    destination = Path(output_path)
    if destination.suffix.lower() != '.png' or not destination.parent.is_dir() or destination.exists():
        raise ValueError('output must be a new PNG in an existing local directory')
    quality_destination = None
    if quality_json_path is not None:
        quality_destination = Path(quality_json_path)
        if (quality_destination.suffix.lower() != '.json' or
                not quality_destination.parent.is_dir() or quality_destination.exists() or
                quality_destination == destination):
            raise ValueError('quality output must be a new JSON in an existing local directory')
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
    ordered = [frames[i] for i in ids]
    if projective and (anchored or audit_loops or len(ordered) < 3):
        raise ValueError('projective preview requires 3-4 frames without --anchored or --audit-loops')
    if audit_loops:
        if not anchored or len(ordered) < 3:
            raise ValueError('loop audit requires --anchored and at least three RGB frames')
        findings = audit_visual_loops(ordered)
        failures = [f for f in findings if not f.passes]
        if failures:
            pairs = ', '.join(f'{ids[f.start_index]}-{ids[f.end_index]}' for f in failures)
            raise ValueError(f'inconsistent or unverifiable visual loops: {pairs}')
    result = (compose_projective_visual_preview(ordered) if projective else
              (compose_anchored_visual_preview if anchored else compose_visual_strip)(ordered))
    quality_text = projective_quality_json(result) if quality_destination is not None else None
    ok, png = cv2.imencode(".png", cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("PNG encoding failed")
    with destination.open("xb") as stream:
        stream.write(png.tobytes())
    if quality_destination is not None:
        with quality_destination.open('x', encoding='utf-8') as stream:
            stream.write(quality_text)
    return result.pair_inliers


def main(argv=None):
    parser = argparse.ArgumentParser(description="NON-METRIC offline RGB visual strip (2-4 frames)")
    parser.add_argument("archive")
    parser.add_argument("output_png")
    parser.add_argument("frame_ids", nargs="+")
    parser.add_argument("--anchored", action="store_true", help="warp each original frame once into first-frame coordinates; non-metric")
    parser.add_argument("--audit-loops", action="store_true", help="fail closed on inconsistent or unverifiable multi-frame loops")
    parser.add_argument("--projective", action="store_true", help="global projective visual preview; NON-METRIC")
    parser.add_argument("--quality-json", help="optional new nonmetric projective quality JSON path")
    args = parser.parse_args(argv)
    try:
        counts = preview_rgb_strip(args.archive, args.frame_ids, args.output_png, anchored=args.anchored, audit_loops=args.audit_loops, projective=args.projective, quality_json_path=args.quality_json)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Visual strip failed: {exc}\n")
    print(f"NON-METRIC visual strip, NOT an orthophoto; RANSAC inliers per stage: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
