"""Optional local flight-overview illustration with explicit flight-path provenance."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PilotFlightOverview:
    image_path: Path | None = None
    path_kind: str = "not_available"
    source_note: str = "nicht erfasst"

    def __post_init__(self):
        if self.path_kind not in {"recorded", "planned", "illustrative", "not_available", "nonmetric_visual"}:
            raise ValueError("unknown flight-path provenance")
        if self.image_path is not None:
            path = Path(self.image_path)
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                raise ValueError("flight overview must be a local PNG or JPEG file")
        if not isinstance(self.source_note, str) or not self.source_note.strip():
            raise ValueError("flight overview source note required")


def flight_overview_label(overview: PilotFlightOverview | None) -> str:
    if overview is None:
        return "Kein verifizierter Flugpfad oder RGB-Orthofoto verfügbar."
    if overview.path_kind == "not_available":
        if overview.image_path is not None:
            return "RGB-Orthofoto-Übersicht vorhanden; kein verifizierter Flugpfad verfügbar."
        return "Kein verifizierter Flugpfad oder RGB-Orthofoto verfügbar."
    return {
        "nonmetric_visual": "Nicht metrisch verifizierte Bildvorschau – kein Orthofoto und kein Flugpfadnachweis",
        "recorded": "Tatsächlich aufgezeichneter Flugpfad",
        "planned": "Geplanter Flugpfad – kein Nachweis des tatsächlichen Flugs",
        "illustrative": "Schematische Flugroute – ausschließlich Layoutbeispiel",
    }[overview.path_kind]
