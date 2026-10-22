# Optionale RGB-/Thermal-Kontrollpunktprüfung – Offline-Pilot

## Abgrenzung

Die normale DJI-M3T-Aufnahmezuordnung (gleiche Aufnahme-IDs und Zeit-/GPS-Nähe) erzeugt **nur technische Bildpaare**. Pixelregistrierung ist eine eigenständige Stufe. Diese erste Expertenfunktion beurteilt ausschließlich eine vom Menschen lokal bereitgestellte Kontrollpunkt-Hypothese; sie erzeugt keine Bildüberlagerung und nimmt keine Projektfreigabe vor.

## Bedienung

1. Im Offline-SolarCheck das Projekt öffnen, das bereits mindestens ein gespeichertes RGB-/Thermal-Paar hat.
2. **Verarbeitung → Erweitert: Kontrollpunktprüfung anzeigen** wählen.
3. **Lokale Kontrollpunkt-Datei prüfen (JSON)** auswählen.
4. Eine kleine, selbst erstellte JSON-Datei mit der **tatsächlich gespeicherten `pair_id` dieses Projekts** verwenden. Nicht raten: Identitäten sind projektlokal, keine frei erfindbaren Paar-IDs.
5. Das Ergebnis zeigt nur Inlier-, Holdout-Anzahl, RMS-Pixelabweichung oder einen generischen Ablehnungsgrund. Die Datei, die Bilder und SQLite bleiben unverändert.

## Dateiformat

```json
{
  "schema": 1,
  "pair_id": "<vorhandene_pair_id_des_aktiven_projekts>",
  "fit_points": [
    [30, 40, 250, 280],
    [130, 60, 750, 380],
    [240, 90, 1300, 530],
    [80, 220, 500, 1180],
    [330, 180, 1750, 980],
    [500, 410, 2600, 2130]
  ],
  "holdout_points": [
    [95, 85, 575, 505],
    [225, 175, 1225, 955],
    [320, 340, 1700, 1780],
    [425, 260, 2225, 1380]
  ]
}
```

Die Koordinaten sind **ausschließlich synthetische Formatbeispiele**, keine erfassten echten DJI-M3T-Kontrollpunkte. Diese Datei ist **nicht** unmittelbar für einen Kundenbericht geeignet; die `pair_id` muss aus dem tatsächlichen lokalen Projektdatensatz stammen. Die beiden Gruppen müssen räumlich sinnvolle, voneinander unabhängige Beobachtungen enthalten. Automatisches oder nachträgliches Auswählen der Holdoutpunkte aus einem bereits angepassten Transform verletzt die Unabhängigkeitsannahme.

## Prüfkriterien und Grenzen

- Mindestens 6 Anpassungs- und 4 Holdoutpunkte, keine doppelten Anpassungskoordinaten und keine überschneidenden Thermalpunkt-Positionen zwischen Fit/Holdout
- Manuelle Koordinaten müssen endlich und innerhalb beider Sensorbilder liegen; Sensorabmessungen werden aus der bestehenden Projekt-SQLite gelesen
- Nicht kollineare Fit-Geometrie, OpenCV-RANSAC und mindestens sechs Fit-Inlier; maximal 12 Pixel RMS und 30 Pixel maximaler Holdout-Fehler in **RGB-Zielpixeln**
- Keine Originalbilddekodierung, keine Netzwerkverbindung, keine Datenbankänderung, keine persistierte Transformationsmatrix und keine automatisierte Fach-, Trainings- oder Berichtsfreigabe
- Nicht nachgewiesen: tatsächliche menschliche Unabhängigkeit der Kontrollpunkte, physische Modulkorrespondenz, geometrische Produktionsfreigabe, metrische Lagegenauigkeit, georeferenzierte Orthofotos und kalibrierte Celsiuswerte

Die vorhandenen globalen PV-Gitterverfahren können mathematisch extrapolierte Linien-Schnittpunkte verwenden; dafür gilt das allgemeine Homografie-Gate weiterhin ohne *manuelle* Randpflicht. Externe, manuell spezifizierte Kontrollpunkte erhalten die strengere Prüfung. Ein erfolgreiches numerisches Holdout ist vor realer Registrierung durch Experten mit geeigneten unabhängigen Referenzen zu bestätigen.
