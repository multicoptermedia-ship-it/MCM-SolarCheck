"""Shared fail-closed contract for calibrated Celsius evidence."""
from __future__ import annotations

from math import isfinite


def has_validated_celsius(value: float | None, status: str | None, provider: str | None) -> bool:
    """Return true only for finite Celsius evidence with explicit provenance."""
    if value is None or status != "calibrated" or not (provider and provider.strip()):
        return False
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False
