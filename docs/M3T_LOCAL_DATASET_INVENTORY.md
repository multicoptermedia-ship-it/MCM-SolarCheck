# DJI Mavic 3 Thermal – lokaler Datensatz thermal3/vis3

Bestand aus lokal bereitgestellten ZIP-Archiven, **ohne Bild-Upload ins Repository**.

- `thermal3.zip`: 36 Dateien nach Muster `DJI_20250825..._NNNN_T.JPG`, Sequenzen 0001–0036.
- `vis3.zip`: 29 Dateien nach Muster `DJI_20250825..._NNNN_V.JPG`, Sequenzen 0001–0029.
- 29 Sequenzen besitzen beide Modalitäten; sieben Thermaldateien (0030–0036) haben kein RGB-Gegenstück in diesem Datensatz.
- Beide ZIP-Dateien sind lesbar und enthalten keine beschädigten ZIP-Einträge (lokale Prüfung).
- Die Dateien sind vom Anwender als DJI-M3T-Aufnahmen bestätigt. Radiometrische APP3-Kompatibilität, GPS-/Zeitmetadaten, Paarungssicherheit und Anomaliequalität sind durch diese Inventur **nicht** validiert.

## Konsequenz
Die bestehende `analyze_imported_m3t_candidates`-Funktion bricht bei nicht vollständig gepaarten Thermalaufnahmen ab. Das bleibt als konservativer Standard bestehen. Für einen bewusst eingeschränkten Prüfmodus wird eine **explizite Teilmengenfreigabe** benötigt; ungepaarte Thermalbilder bleiben dokumentiert und dürfen nicht unbemerkt als vollständige Inspektion erscheinen.

Keine Kundenbilder oder GPS-Daten werden committed. Kein Online-/IONOS-Upload.
