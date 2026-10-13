"""Validated orthomosaic presentation manifest; never synthesizes mosaics."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class OrthomosaicLayer:
    image_url: str
    width: int
    height: int
    source: str


@dataclass(frozen=True)
class RegisteredOrthomosaicPair:
    project_id: str
    rgb: OrthomosaicLayer
    thermal: OrthomosaicLayer
    registration_verified: bool
    coordinate_system: str
    registration_reference: str

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project identifier required")
        if not self.registration_verified or not self.registration_reference.strip():
            raise ValueError("verified registration and evidence required")
        if not self.coordinate_system.strip():
            raise ValueError("coordinate system required")
        if self.rgb.width != self.thermal.width or self.rgb.height != self.thermal.height:
            raise ValueError("viewer layers must share a registered pixel grid")
        for layer in (self.rgb, self.thermal):
            if layer.width < 1 or layer.height < 1:
                raise ValueError("invalid orthomosaic dimensions")
            if layer.source not in ("rgb_orthomosaic", "thermal_visualization"):
                raise ValueError("unsupported layer provenance")
            parsed = urlsplit(layer.image_url)
            if (parsed.scheme or parsed.netloc or not parsed.path.startswith("/")
                    or parsed.path.startswith("//") or parsed.fragment
                    or "\\" in layer.image_url):
                raise ValueError("orthomosaic URLs must be same-origin absolute paths")
        if self.rgb.source != "rgb_orthomosaic" or self.thermal.source != "thermal_visualization":
            raise ValueError("incorrect layer roles")

    def to_viewer_manifest(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "registration_verified": True,
            "coordinate_system": self.coordinate_system,
            "registration_reference": self.registration_reference,
            "width": self.rgb.width,
            "height": self.rgb.height,
            "rgb_url": self.rgb.image_url,
            "thermal_url": self.thermal.image_url,
            "thermal_is_visualization_only": True,
        }
