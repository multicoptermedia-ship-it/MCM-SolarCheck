"""Small bounded RGB segment renderer; working frames only, not native mosaic."""
import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_canvas_plan import plan_rgb_canvas


def render_rgb_segment(segment, frames, *, max_pixels=12_000_000):
    """Warp bounded working RGB frames into a nonmetric blended preview."""
    dimensions = {key: (frame.shape[1], frame.shape[0]) for key, frame in frames.items()}
    plan = plan_rgb_canvas(segment, dimensions, max_pixels=max_pixels)
    width, height = plan["width"], plan["height"]
    left, top = plan["origin"]
    shift = np.array([[1, 0, -left], [0, 1, -top], [0, 0, 1]], dtype=np.float64)
    sums = np.zeros((height, width, 3), dtype=np.float32)
    counts = np.zeros((height, width), dtype=np.float32)
    for key, raw in segment["frames"].items():
        if key not in frames:
            raise ValueError("missing RGB frame")
        frame = frames[key]
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("expected uint8 RGB frame")
        transform = shift @ np.asarray(raw, dtype=np.float64)
        warped = cv2.warpPerspective(frame, transform, (width, height))
        mask = cv2.warpPerspective(np.ones(frame.shape[:2], dtype=np.uint8),
                                   transform, (width, height), flags=cv2.INTER_NEAREST)
        sums += warped.astype(np.float32) * mask[..., None]
        counts += mask
    output = np.zeros((height, width, 3), dtype=np.uint8)
    valid = counts > 0
    output[valid] = np.clip(sums[valid] / counts[valid, None], 0, 255).astype(np.uint8)
    return output, {"canvas": plan, "nonmetric": True, "native_resolution": False}
