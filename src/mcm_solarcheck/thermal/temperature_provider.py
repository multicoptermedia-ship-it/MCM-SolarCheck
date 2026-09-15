"""Temperature conversion provider boundary.

Raw M3T radiometric samples are deliberately kept separate from calibrated
Celsius values. A provider must be validated against an authoritative
reference implementation before its output is accepted by production code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


class TemperatureConversionUnavailable(RuntimeError):
    """Raised when no validated radiometric conversion backend is available."""


@dataclass(frozen=True)
class TemperatureMatrix:
    width: int
    height: int
    values_celsius: tuple[float, ...]
    provider: str
    provider_version: str | None = None

    def __post_init__(self) -> None:
        if len(self.values_celsius) != self.width * self.height:
            raise ValueError("Temperature matrix size does not match dimensions")


class ThermalTemperatureProvider(Protocol):
    """Interface for authoritative raw/R-JPEG -> Celsius conversion backends."""

    @property
    def name(self) -> str: ...

    def convert_file(self, path: str | Path) -> TemperatureMatrix:
        """Return a calibrated per-pixel Celsius matrix for one thermal file."""
        ...


class DJIReferenceTemperatureProvider:
    """Boundary for a future validated DJI offline radiometric backend.

    This intentionally does not implement a guessed conversion formula.
    """

    name = "dji-reference"

    def convert_file(self, path: str | Path) -> TemperatureMatrix:
        raise TemperatureConversionUnavailable(
            "DJI M3T Celsius conversion backend has not yet been validated/configured"
        )
