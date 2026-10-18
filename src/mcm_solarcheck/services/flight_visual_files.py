"""Local individual RGB files to a non-metric preview and quality JSON."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mcm_solarcheck.services.visual_projective_preview import compose_projective_visual_preview
from mcm_solarcheck.services.visual_quality_export import projective_quality_json


def preview_rgb_files(image_paths, output_path, quality_json_path, *, max_image_bytes=80_000_000, max_side=800):
    """Use the shared registration/preview core; no ZIP or EXIF required."""
    paths = tuple(Path(p) for p in image_paths)
    if len(paths) not in (3, 4) or len(set(paths)) != len(paths):
        raise ValueError("select 3-4 distinct RGB images")
    if type(max_image_bytes) is not int or max_image_bytes <= 0 or type(max_side) is not int or max_side < 128:
        raise ValueError("invalid resource limits")
    png, quality = Path(output_path), Path(quality_json_path)
    if (png.suffix.lower() != ".png" or quality.suffix.lower() != ".json" or
            not png.parent.is_dir() or not quality.parent.is_dir() or
            png.exists() or quality.exists()):
        raise ValueError("outputs must be new PNG and JSON files in existing directories")
    frames = []
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("each RGB input must be a local JPEG or PNG")
        if path.stat().st_size > max_image_bytes:
            raise ValueError("oversized RGB input")
        raw = path.read_bytes()
        if len(raw) > max_image_bytes:
            raise ValueError("oversized RGB input")
        decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("unreadable RGB input")
        height, width = decoded.shape[:2]
        scale = min(1., max_side / max(height, width))
        if scale < 1:
            decoded = cv2.resize(decoded, (max(1, round(width * scale)), max(1, round(height * scale))))
        frames.append(cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB))
    result = compose_projective_visual_preview(frames)
    quality_text = projective_quality_json(result)
    ok, encoded = cv2.imencode(".png", cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("PNG encoding failed")
    with png.open("xb") as stream:
        stream.write(encoded.tobytes())
    with quality.open("x", encoding="utf-8") as stream:
        stream.write(quality_text)
    return result
