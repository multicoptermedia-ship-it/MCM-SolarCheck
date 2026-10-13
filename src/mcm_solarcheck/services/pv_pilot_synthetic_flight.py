"""Synthetic flight-path illustration; never presented as a real orthophoto."""
from pathlib import Path

from PIL import Image, ImageDraw

from mcm_solarcheck.services.pv_pilot_flight_overview import PilotFlightOverview


def fictional_flight_overview(directory: Path) -> PilotFlightOverview:
    destination = directory / "fictional-flight-overview.png"
    image = Image.new("RGB", (1200, 750), (90, 116, 83))
    draw = ImageDraw.Draw(image)
    for row in range(5):
        for col in range(10):
            x, y = 100 + col * 100, 100 + row * 120
            draw.rectangle((x, y, x + 78, y + 85), fill=(31, 62, 83), outline=(180, 198, 206), width=2)
    path = [(70, 145), (1100, 145), (1100, 265), (70, 265),
            (70, 385), (1100, 385), (1100, 505), (70, 505),
            (70, 625), (1100, 625)]
    draw.line(path, fill=(255, 223, 39), width=9)
    draw.text((25, 20), "FIKTIVE SCHEMATISCHE FLUGROUTE - KEIN ORTHOFOTO", fill="white")
    draw.text((25, 710), "Keine Wegpunkte; kein Flugnachweis", fill="white")
    image.save(destination)
    return PilotFlightOverview(destination, "illustrative", "synthetische Illustration, keine realen Flugdaten")
