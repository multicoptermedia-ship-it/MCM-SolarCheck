# 160 RGB-Originalbilder → externes 2D-Orthofoto → SolarCheck

**Verbindlicher einfacher Weg:** Ein bestehender, etablierter Orthofoto-Prozessor übernimmt die Bildberechnung. **Keine eigene SolarCheck-Orthofoto-Engine, kein erneut erfundener Stitch-Algorithmus.** Das fertige Produkt ist ein **zweidimensionales RGB-GeoTIFF**.

## Bereits bereit
- Sechs inventarisierte Hummintech-ZIP/`.tip` mit 160 DJI M3T WideCamera-RGB-Fotos V-0001…V-0160 (4000×3000), sieben Streifen und GNSS/RTK im EXIF/XMP. **Keine neue ZIP-, EXIF-, ORB- oder Paar-Inventur.**
- SolarCheck **Importseite**: „GeoTIFF / GIS-Metadaten prüfen“ und „GeoTIFF dauerhaft im Projekt registrieren“ sind bereits implementiert (`src/mcm_solarcheck/gui/import_page.py`); die Prüfung erfolgt über `inspect_existing_geotiff`. Die Registrierung ist nur ein **Metadatenimport**, keine fachliche Freigabe.
- Für Berichte existiert `create_rgb_orthophoto_report_preview` für echtes RGB-uint8-GeoTIFF.

## Einziger nächster praktischer Schritt auf dem vorhandenen Windows-Rechner
1. **Externe Pilotsoftware:** [Agisoft Metashape Professional](https://www.agisoft.com/features/professional-edition/) mit [Windows-Installer / 30-Tage-Vollfunktions-Test](https://www.agisoft.com/downloads/installer/), sofern Nutzer das Programm lokal installiert und aktiviert. **Kein automatischer Kauf, Download oder App-Einbau.** Andere bereits lizenzierte professionelle Orthofoto-Software mit GeoTIFF-Export ist genauso geeignet.
2. Kunden-ZIP-Originale **read-only lassen**. Fotos nur soweit erforderlich in ein getrenntes, privates Arbeitsverzeichnis kopieren/extrahieren. **Keine** Fotos, Metadaten, lokalen Koordinaten oder Raster nach GitHub/Cloud. Die Lizenzaktivierung ist von der lokalen Fotoverarbeitung zu unterscheiden.
3. Alle **160** RGB-Fotos im lokalen Fachprogramm laden; vorhandene Aufnahme-/GNSS-Metadaten nutzen, Bilder ausrichten. Echte geneigte Dachflächen erfordern eine geeignete Orthorektifizierungsoberfläche; die nötige interne Berechnung macht das externe Programm. Kein eigenes 3D-Programm in SolarCheck entwickeln, kein 3D-Modell als Nutzerprodukt.
4. Orthomosaik mit passender Bildquellen-/Naht- und optional Ghosting-Korrektur erzeugen; **RGB GeoTIFF mit explizitem CRS/EPSG** lokal exportieren. **Scharfe PV-Modulkanten, Doppelkonturen, Nahtübergänge und Vollständigkeit** gegen die Problemzonen des gescheiterten 28.10.-160-Bild-Tests prüfen. Wenn schlecht: im vorhandenen Fachprogramm korrigieren, nicht neue Algorithmen programmieren.
5. SolarCheck-Projekt öffnen → **Import → GeoTIFF / GIS-Metadaten prüfen** → neue TIFF auswählen und CRS/Raster prüfen → **GeoTIFF dauerhaft im Projekt registrieren**. Das ist keine unabhängige metrische Vermessungsfreigabe. PV-ID-/Thermal-Verknüpfung erst nach Sichtkontrolle und Geometrieprüfung.

## Abgrenzung
- Die vorliegende GitHub-Pipeline hat den echten 160-Bild-Flug **nicht** erfolgreich nachgerechnet. Das alte Gesamtbild hatte Doppelkonturen und unscharfe PV-Module, Einzelstreifen waren besser. Hier fehlen derzeit die echten Originalarchive und die frühere Vorschau.
- **Keine ODM/WebODM/ODX-Integration** (alte Projektschranke unverändert), keine neue Abhängigkeit, kein 3D-Produkt. Ein rein projektiver OpenCV-Stitcher ist bei verschiedenen geneigten Dächern **kein** verlässlicher Ersatz für Orthorektifizierung.

Herstellerquellen: [Metashape Professional](https://www.agisoft.com/features/professional-edition/), [Metashape Installer/Test](https://www.agisoft.com/downloads/installer/), [Unterschied Stitching und Orthomosaik](https://support.pix4d.com/hc/en-us/articles/202558869).
