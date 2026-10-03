"""Pair RGB and thermal frames using sequence, time and position evidence."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
import re

from mcm_solarcheck.domain.models import ImageFrame, ImagePair, ThermalFrame

_SEQ_RE = re.compile(r"_(\d{4})_[VT]\.JPG$", re.IGNORECASE)


def sequence_number(frame: ImageFrame) -> str | None:
    match = _SEQ_RE.search(frame.source_file.name)
    return match.group(1) if match else None


def _distance_m(a: ImageFrame, b: ImageFrame) -> float | None:
    if a.position is None or b.position is None:
        return None
    lat1, lon1 = radians(a.position.latitude), radians(a.position.longitude)
    lat2, lon2 = radians(b.position.latitude), radians(b.position.longitude)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371008.8 * asin(sqrt(h))


def _time_delta_s(a: ImageFrame, b: ImageFrame) -> float | None:
    if a.timestamp_utc is None or b.timestamp_utc is None:
        return None
    return abs((a.timestamp_utc - b.timestamp_utc).total_seconds())


def pair_score(rgb: ImageFrame, thermal: ThermalFrame) -> tuple[float, str, float | None, float | None]:
    """Return conservative confidence and evidence for one potential pair."""
    score = 0.0
    methods: list[str] = []
    rgb_seq, thermal_seq = sequence_number(rgb), sequence_number(thermal)
    if rgb_seq is not None and rgb_seq == thermal_seq:
        score += 0.65
        methods.append("sequence")

    dt = _time_delta_s(rgb, thermal)
    if dt is not None:
        if dt <= 0.25:
            score += 0.20
            methods.append("time")
        elif dt <= 1.0:
            score += 0.10
            methods.append("time")

    distance = _distance_m(rgb, thermal)
    if distance is not None:
        if distance <= 0.5:
            score += 0.15
            methods.append("position")
        elif distance <= 2.0:
            score += 0.05
            methods.append("position")

    return min(score, 1.0), "+".join(methods) or "none", distance, dt


def pair_rgb_thermal_frames(
    rgb_frames: tuple[ImageFrame, ...],
    thermal_frames: tuple[ThermalFrame, ...],
    *,
    minimum_confidence: float = 0.70,
) -> tuple[ImagePair, ...]:
    """Greedily select unique high-confidence RGB/Thermal pairs."""
    candidates = []
    for rgb in rgb_frames:
        for thermal in thermal_frames:
            confidence, method, distance, dt = pair_score(rgb, thermal)
            if confidence >= minimum_confidence:
                candidates.append((confidence, rgb.frame_id, thermal.frame_id, method, distance, dt))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))

    used_rgb: set[str] = set()
    used_thermal: set[str] = set()
    pairs: list[ImagePair] = []
    for confidence, rgb_id, thermal_id, method, distance, dt in candidates:
        if rgb_id in used_rgb or thermal_id in used_thermal:
            continue
        used_rgb.add(rgb_id)
        used_thermal.add(thermal_id)
        pairs.append(ImagePair(
            pair_id=f"PAIR-{rgb_id}-{thermal_id}", rgb_frame_id=rgb_id,
            thermal_frame_id=thermal_id, confidence=confidence, method=method,
            distance_m=distance, time_delta_s=dt,
        ))
    return tuple(pairs)
