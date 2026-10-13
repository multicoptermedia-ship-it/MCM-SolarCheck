"""Generate synthetic, clearly labelled image fixtures; no customer imagery."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

from mcm_solarcheck.services.pv_pilot_pdf_evidence import PilotEvidence


def synthetic_evidence(directory: Path) -> tuple[PilotEvidence, ...]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for label, color in (("rgb", (35, 86, 125)), ("thermal", (146, 71, 40))):
        path = directory / ("fictional_" + label + ".png")
        image = Image.new("RGB", (960, 540), (239, 242, 245))
        draw = ImageDraw.Draw(image)
        for row in range(2):
            for col in range(5):
                x, y = 85 + col * 155, 95 + row * 165
                draw.rectangle((x, y, x + 130, y + 140), fill=color, outline=(15, 30, 45), width=4)
                draw.line((x + 65, y, x + 65, y + 140), fill=(215, 222, 227), width=2)
        draw.text((24, 20), "FIKTIVES TESTBILD - KEINE INSPEKTION", fill=(12, 22, 32))
        draw.text((24, 505), label.upper() + " - schematische Darstellung, keine Messwerte", fill=(12, 22, 32))
        image.save(path)
        paths.append(path)
    return (PilotEvidence(
        module="M-01 (fiktiv)", rgb_path=paths[0], thermal_path=paths[1],
        rgb_frame="SYNTHETIC-RGB", thermal_frame="SYNTHETIC-THERMAL",
        rgb_geometry="schematisch, nicht georeferenziert",
        thermal_geometry="schematisch, nicht georeferenziert",
    ),)
