# Freie Orthofoto-Werkzeuge: Auswahl und belegter Prüfstand

Stand **31.10.2026**. Maßgeblich ist [AKTUELLER_ENTWICKLUNGSSTAND.md](AKTUELLER_ENTWICKLUNGSSTAND.md). Ziel sind lokale RGB- und Thermal-Orthofotos, der [bestehende GeoTIFF-Import](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md), PV-Modulerkennung und Thermal-Zuordnung. Keine neue Engine; keine proprietären/kostenpflichtigen Programme, kein ODM/WebODM/ODX.

## Vergleich

| Werkzeug | Belegte Rolle und Lizenz | Bewertung für SolarCheck |
| --- | --- | --- |
| **MicMac v1.2.0** | CeCILL-B-Hauptprojekt; etablierte Luftbild-Photogrammetrie mit `Malt Ortho`/`Tawny`, native Windows-Ausgabe. | Priorisierter technischer Kandidat. Abweichende Komponentenbedingungen verhindern derzeit die pauschale Freigabe einer konkreten Distribution; siehe unten. |
| **MMVII / MicMac V2** | CeCILL-B. Aktuelles offizielles README benötigt MicMac V1 nicht mehr; Windows-Binärpaket vorhanden. | Separater Kandidat; vollständige RGB-/Thermal-Orthofoto-Kette und Austauschbarkeit der V1-Kommandos wurden hier nicht belegt. |
| **COLMAP** | BSD-Hauptlizenz, Abhängigkeiten separat lizenziert; etablierte Kameraorientierung/Rekonstruktion. | Kein direkt belegter vollständiger GeoTIFF-/Thermal-Orthofotoablauf. Laut offizieller FAQ benötigt dichte Rekonstruktion CUDA; CPU-SfM kann Teil einer separat geprüften freien Kette sein. |
| **OpenMVS** | AGPL-3.0. Aktuelle offizielle Dokumentation beschreibt native `CreateStructure`-SfM sowie CPU-Verarbeitung. | Reale Alternative für Rekonstruktion/Mesh/Textur. `TextureMesh` erzeugt aus georeferenziertem/ausgerichtetem Mesh ein orthografisches PNG plus TXT, noch kein importfertiges GeoTIFF oder quantitativer Thermalnachweis. |
| **OpenMVG** | MPL-2.0; etablierte SfM-Software. | Orientierung als Teil einer externen Werkzeugkette, allein kein vollständiger Orthofoto-Erzeuger. |
| **QGIS / GDAL / OTB** | Freie GIS-/Rasterwerkzeuge mit eigenen Lizenzen. | Prüfung, Konvertierung, bekannte Georeferenzierung und Reprojektion. Sie ersetzen nicht automatisch die Kameralösung/Oberfläche aus DJI-Einzelfotos. OTB-Orthorektifizierung braucht unterstützte Sensorgeometrie und Höheninformationen. |

Keine Zeile ist eine Weiterverteilungsfreigabe aller optionalen Komponenten oder ein erfolgreicher DJI-M3T-Reallauf. SolarCheck kopiert keine Algorithmen daraus.

## MicMac: Hauptlizenz und tatsächliche Komponenten unterscheiden

Das [offizielle README v1.2.0](https://github.com/micmacIGN/micmac/blob/v1.2.0/README.md) beschreibt freie IGN/ENSG-Software unter CeCILL-B und Windows 10. [Release v1.2.0 vom 10.06.2026](https://github.com/micmacIGN/micmac/releases/tag/v1.2.0) bietet native Windows-/Linux-Archive. Das belegt Verfügbarkeit, keine hier erfolgte Installation/Windows-Abnahme. [LICENSE.md](https://github.com/micmacIGN/micmac/blob/v1.2.0/LICENSE.md) und [COPYING](https://github.com/micmacIGN/micmac/blob/v1.2.0/COPYING) enthalten die CeCILL-B-Hauptlizenz.

Konkrete abweichende Quelltexte:

- **SiftPP:** [notice.txt](https://github.com/micmacIGN/micmac/blob/v1.2.0/CodeExterne/Siftpp/notice.txt) und Quellcode erlauben Verwendung/Kopieren/Weitergabe ausdrücklich für „educational, research and non-profit purposes“; [README](https://github.com/micmacIGN/micmac/blob/v1.2.0/CodeExterne/Siftpp/README) nennt eine erforderliche Erlaubnis für kommerzielle Verwendung. Patentablauf beseitigt urheberrechtliche Bedingungen nicht automatisch. `CodeExterne/Siftpp` ist kein eigener regulärer CMake-Unterbuild; der ältere externe Helfer ist dennoch der Vorgabedetektor von `Pastis`.
- **Shewchuk/Triangle:** [README](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/geom2d/Shewchuk.README) und [Quellkopf](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/geom2d/Shewchuk_implem.cpp) erlauben freie Weitergabe mit erhaltenen Hinweisen, verlangen aber für Weiterverteilung als Teil eines kommerziellen Systems eine direkte Vereinbarung. Die normale **Nutzung** ist davon zu unterscheiden. [geom2d/Sources.cmake](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/geom2d/Sources.cmake) nimmt die Implementierung regulär in `Elise_Src_Files` auf; [src/CMakeLists.txt](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/CMakeLists.txt) baut daraus `libelise`. Eine zusätzliche aktuelle Rechteklärung oder ein nachweislich bereinigtes Binärpaket ist hier nicht belegt.
- **Optionale Komponenten:** [CMakeLists.txt](https://github.com/micmacIGN/micmac/blob/v1.2.0/CMakeLists.txt) setzt `WITH_KAKADU` und `CUDA_ENABLED` auf `OFF`; der Quellbaum enthält außerdem ältere SiftGPU-/CUDA-Binärhelfer. Diese nicht aktivieren/bündeln. Die Schalter klären nicht die reguläre Triangle-Komponente.

Daraus folgt **nicht**, dass jede MicMac-Nutzung proprietär oder unzulässig sei. Die Hauptlizenz allein belegt aber keine vollständig freie konkrete Binär-/Weiterverteilungskette für SolarCheck. Eine separat installierte EXE ist ebenfalls kein automatischer Nachweis. Bis zur passenden Komponenten-/Rechteklärung keine automatische Installation, Bündelung oder als freigegeben dargestellte Ausführung aus SolarCheck.

## Vorhandene Standardpipeline statt Nachbau

Die [offiziellen vereinfachten Werkzeuge](https://github.com/micmacIGN/Documentation/blob/master/DocMicMac/Generalites/QuickStartSimplified-Tools.tex) und das [Luftbildbeispiel mit GPS](https://github.com/micmacIGN/Documentation/blob/master/DocMicMac/Generalites/QuickStartSimplified-Tools-2.tex) dokumentieren:

1. `Tapioca` für Korrespondenzen, `Tapas` für Orientierung/Kameramodell. Die vorhandenen Werkzeuge schätzen Kameraparameter; eine externe Kalibrierungsdatei ist keine allgemeine RGB-Voraussetzung.
2. Georeferenzierung mit `OriConvert`, `CenterBascule` und `Campari` unter Verwendung tatsächlicher Koordinaten/CRS. Relative Orientierung allein erzeugt keine metrische Weltreferenz.
3. `Malt Ortho` und `Tawny` für Orthorektifizierung/Mosaik; alternativ dokumentierte `PIMs`/`PIMs2Mnt`-Kette. Diese Stufen nicht in SolarCheck neu implementieren.

[Tapioca](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/CPP_Tapioca.cpp) unterstützt `Detect=mm3d:Digeo Match=mm3d:Ann`; die [Optionsnamen](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/CPP_Pastis.cpp) sind belegt. Damit lassen sich ältere externe Detektor-/Matcherhelfer vermeiden. **Das klärt nicht die gesamte Laufzeit**, insbesondere nicht Triangle. Kein automatisch ausführbares SolarCheck-Skript wird deshalb als bereits freigegeben ausgegeben.

## GeoTIFF und Thermal

Ein TIFF/Worldfile ist nicht automatisch ein GeoTIFF mit eingebettetem CRS. Eine Worldfile-Transformation enthält keinen EPSG-Nachweis. [GDAL](https://gdal.org/en/stable/drivers/raster/gtiff.html) kann bekannte Referenzen lesen und als GeoTIFF speichern; [gdal_translate](https://gdal.org/en/stable/programs/gdal_translate.html) weist mit `-a_srs` ein bekanntes CRS zu, reprojiziert aber nicht. Fehlende Geometrie nicht durch einen geratenen EPSG-Code ersetzen. Für den vorhandenen SolarCheck-Import echte eingebettete Referenz und gültige Maske/NoData bereitstellen.

RGB und Thermal brauchen eigene Sensorparameter und eine passende gemeinsame räumliche Referenz. Farbige Thermalbilder sind Darstellungen; Temperaturbefunde brauchen nachgewiesene Werte mit Einheiten, Skalierung/Offset und NoData. Den bereits untersuchten mittigen Temperaturpunkt wiederverwenden, daraus keine vollständige Temperaturmatrix oder Sensorregistrierung ableiten.

[Tawny v1.2.0](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/CPP_Tawny.cpp) aktiviert radiometrischen Ausgleich standardmäßig. Bei numerischen Temperaturdaten `RadiomEgal=0`; zusätzlich Datentyp, Resampling, Masken und Werteerhalt durch die gesamte Kette prüfen. Diese Option allein ist keine Thermal-Freigabe.

## Belegter Umfang

Öffentliche Upstream-Quellen/Dokumentation geprüft; keine Kundenbilder/GPS/RTK verarbeitet/übertragen, keine Binärpakete installiert/ausgeführt und keine eigene Photogrammetrie gerechnet. Synthetische TIFF-Regressionen prüfen SolarChecks Import-/Masken-/Zuordnungslogik, keine echte Windows-10-/Orthofotoqualität.

Zuerst bestehende GeoTIFF-Übergabe für beide Raster sowie PV-/Thermal-Zuordnung nutzen. Konkrete freie Werkzeugzusammenstellung gesondert belegen und anschließend ausschließlich lokal beim Nutzer mit echten Aufnahmen prüfen. Kein neuer Engine-, Gate- oder Rohbildinventur-Nebenweg. Kein Merge nach `main`.

Weitere Primärquellen: [MMVII](https://github.com/micmac-V2/MMVII), [COLMAP-Lizenz](https://github.com/colmap/colmap/blob/main/LICENSE), [CPU/GPU und Georegistrierung](https://colmap.github.io/faq.html), [OpenMVS AGPL](https://github.com/cdcseacave/openMVS/blob/master/LICENSE), [aktueller OpenMVS-Ablauf](https://github.com/cdcseacave/openMVS/wiki/Usage), [OpenMVS-Orthobildausgabe](https://github.com/cdcseacave/openMVS/blob/master/apps/TextureMesh/TextureMesh.cpp), [OpenMVG MPL](https://github.com/openMVG/openMVG/blob/develop/LICENSE).
