"""Bounded, provenance-tagged candidate pairs for local RGB matching."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidatePair:
    first_id: str
    second_id: str
    reason: str

    def __post_init__(self) -> None:
        if not self.first_id or not self.second_id or self.first_id == self.second_id:
            raise ValueError("candidate needs distinct frame ids")
        if self.reason not in ("consecutive", "cross_strip"):
            raise ValueError("unsupported candidate reason")


def select_overlap_candidates(
    frame_ids: tuple[str, ...],
    *,
    cross_strip_pairs: tuple[tuple[str, str], ...] = (),
    max_candidates: int = 10000,
) -> tuple[CandidatePair, ...]:
    if len(frame_ids) < 2 or len(set(frame_ids)) != len(frame_ids):
        raise ValueError("at least two distinct frame ids required")
    if max_candidates < len(frame_ids) - 1:
        raise ValueError("candidate limit below required consecutive comparisons")
    known = set(frame_ids)
    seen = set()
    result = []
    for first, second, reason in (
        *((a, b, "consecutive") for a, b in zip(frame_ids, frame_ids[1:])),
        *((a, b, "cross_strip") for a, b in cross_strip_pairs),
    ):
        if first not in known or second not in known or first == second:
            raise ValueError("candidate refers to unknown or identical frames")
        key = frozenset((first, second))
        if key in seen:
            continue
        if len(result) >= max_candidates:
            raise ValueError("too many overlap candidates")
        seen.add(key)
        result.append(CandidatePair(first, second, reason))
    return tuple(result)
