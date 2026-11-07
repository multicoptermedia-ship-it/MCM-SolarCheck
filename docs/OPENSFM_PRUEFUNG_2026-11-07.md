# OpenSfM als eigenständiger Orthofoto-Kandidat – 07.11.2026

Nutzerauftrag: das Repository OpenSfM/OpenSfM als Alternative nach gescheitertem MicMac- und COLMAP-Pilot prüfen. Dies ist eine **Quellenprüfung**, keine Installation, Integration oder reale Bildqualitätsabnahme. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md) bleibt der verbindliche Einstieg. RGB **und** Thermal als GeoTIFF sind weiterhin das Ziel, Windows 10 bleibt gesetzt.

## Ergebnis

**OpenSfM ist ein konkreter nächster Kandidat.** Der geprüfte aktuelle Zweig ist die Fortführung des früheren Mapillary-Projekts und enthält inzwischen selbst einen DSM-/Orthofoto-/GeoTIFF-Weg. Die pauschale Aussage, OpenSfM könne nur Kameraposen liefern, wäre für diese Quellen falsch. Ein eingebautes ODM/WebODM/ODX ist dafür nicht erforderlich und wird durch diese Prüfung nicht freigegeben. Keine Algorithmen übernehmen/nachbauen.

Geprüfte Stände: `master` **df1fbb56b2ac387e909003d852761a5bbd0ee619** (03.11.2026) und Release **v1.1 / 8b6b77efddebf4429044d3206c7dc21c4e767e08**, veröffentlicht 16.08.2026. README, Build-/Dense-Dokumentation, Windows-Lockfile und Geräteauswahl sind auch beim Release vorhanden. README nennt 1.0, während pyproject.toml noch 0.5.2 führt; deshalb nicht allein anhand einer Versionszeichenfolge qualifizieren. Den tatsächlichen Quellcommit und Build festhalten.

| Thema | Belegt | Noch offen für SolarCheck |
| --- | --- | --- |
| Rekonstruktion | Metadaten, mehrere Detektoren/Matcher, GPS-/Zeit-/Ähnlichkeits-basierte Paarwahl, Kameramodelle, gemeinsame Ausgleichung. Luftbild-Preset `configs/aerial.yaml` vorhanden. | Vollständiger stabiler Verbund unserer PV-Flugbilder und vertretbare gemessene Laufzeit. Keine Garantie gegenüber COLMAP/WebODM. |
| Orthofoto | Eigene dichte Kette, DSM und RGB+Alpha-GeoTIFF. `dense_merging --georeferenced` nutzt ein projiziertes Ausgabe-CRS, sonst bleibt ein lokales Raster. Ohne projizierte GCP-CRS-Vorgabe wird die passende UTM-Zone abgeleitet. | Tatsächliche Dach-/Modulkanten, Abdeckung, Maßstab, Achsen und unabhängige Lagekontrolle. GPS/RTK allein belegt keine fehlerfreie Rekonstruktion. |
| Windows | Dokumentierter nativer Quellbuild über Conda, `conda-win-64.lock`, MSVC und BAT-Einstiege. Die beiden geprüften GitHub-Releases enthalten keine fertigen Windows-Binärassets. | Konkreter Build/Start unter Windows 10 auf dem Nutzerrechner. Die geprüfte Conda-CI-Matrix nennt Linux/macOS; daraus keinen Windows-10-Nachweis ableiten. |
| Rechenhardware | Sparse-Matcher wie FLANN vorhanden. Dense-Dokumentation verlangt OpenCL-GPU; Python-Geräteauswahl nimmt nur GPU-Geräte und überspringt Intel standardmäßig. Kein klassischer CPU-Fallback dieser Dense-Kette belegt. | OpenCL-Geräte-/Kernelstart, verfügbarer GPU-Speicher und Laufzeit der MX250. Der bekannte CUDA-Treiberfehler ist kein OpenCL-Test; 64 GB System-RAM sind kein GPU-Speicher. Kein Windows-11-/Hardwarewechsel voraussetzen. |
| Thermal | v1.1 nennt ausdrücklich einen behobenen Fehler bei Thermal-Drohnenorthofotos (Issue 22 / PR 23). | Keine belegte M3T-RJPEG-Dekodierung, quantitative Celsiusmatrix oder radiometrische Erhaltung. Dokumentierter Orthoausgang RGB+Alpha; Farbausgleich, Mehrbildmischung, Detailinjektion und Füllungen sind keine unveränderten Sensorwerte. |
| Lizenz | Hauptlizenz BSD-2-Clause, kommerzielle Verwendung unter ihren Bedingungen möglich. Quell- und Binärweitergabe erfordern die entsprechenden Hinweise. | Konkrete Drittkomponenten, Paketkanäle und Weitergabe des gewählten Builds separat prüfen; keine pauschale Freigabe durch die Hauptlizenz. |
| Offline | Verarbeitung kann lokal stattfinden. `proj_cdn_enabled` ist im geprüften Stand standardmäßig wahr und lädt bei Bedarf Datum-/Geoidgitter. Build kann zusätzlich Quell-/Paketabhängigkeiten laden. | Vorbereitung und reine Offline-Laufzeit unterscheiden. Im Kundenlauf Netzzugriffe deaktivieren; benötigte lokale CRS-Gitter vorab prüfen. Kein stiller Online-Fallback. |

## Zusätzlich vom Nutzer genannt: ursprüngliches Mapillary-Repository

[mapillary/OpenSfM](https://github.com/mapillary/OpenSfM) wurde getrennt am Stand **caf3e8f6a3a82af83114d3b58a41dcb3a51a0540** (02.11.2026) geprüft. Das Repository ist laut GitHub nicht archiviert, sein README erklärt aber ausdrücklich, dass es nicht mehr aktiv entwickelt wird, und verweist auf OpenSfM/OpenSfM. Ein neuer Commit-Zeitstempel allein widerlegt diesen Hinweis nicht.

| Unterschied | mapillary/OpenSfM | OpenSfM/OpenSfM (oben geprüft) |
| --- | --- | --- |
| Dense-Rechnung | CPU-C++-Brute-Force/PatchMatch und prozessparallele Python-Steuerung im Quellcode. Kein CUDA-/OpenCL-Zwang dieses älteren Dense-Pfads. | Dokumentierte Dense-Kette mit OpenCL-GPU. CPU-SfM/FLANN und GPU-Dense auseinanderhalten. |
| Ergebnis | Geprüfte `compute_depthmaps`-Kette schreibt zusammengeführte Punktwolke `merged.ply`; OpenMVS-Export vorhanden. Ein eigener vollständiger GeoTIFF-Orthofotoausgang wie im neuen Zweig ist in den geprüften Quellen nicht belegt. | Eigener DSM-/RGB-Orthofoto-/GeoTIFF-Weg dokumentiert und im Code angebunden. |
| Windows | Ältere Build-Anleitung nennt VS2019/Python3.8/vcpkg und enthält inzwischen veraltete Aussagen. Nicht als aktuelle zwingende Versionsvorgaben weitergeben. | Windows-Lockfile/Conda-/MSVC-Weg dokumentiert, reale Windows-10-Qualifizierung trotzdem offen. |
| Lizenz | BSD-2-Clause-Hauptlizenz, Komponenten separat prüfen. | BSD-2-Clause-Hauptlizenz, Komponenten separat prüfen. |

**Folgerung:** Der ältere CPU-Code ist eine relevante Vergleichsquelle für die vorhandene Hardware, liefert aber allein noch keinen nachgewiesenen vollständigen SolarCheck-Orthofoto-Weg. Für den nächsten direkten GeoTIFF-Kandidaten bevorzugt den neuen Zweig qualifizieren. Falls OpenCL konkret scheitert, eine bestehende Sparse→OpenMVS-CPU-Schnittstelle gezielt bewerten; weder alten Dense-/Orthofotocode nachbauen noch beide Wege parallel installieren oder ungeprüft alte und neue Konfigurationen mischen. Keine Qualitäts-/Geschwindigkeitszusage aus der Herkunft als SfM-Kern von WebODM.

Primärquellen der ursprünglichen Version: [README/Wartungshinweis](https://github.com/mapillary/OpenSfM/blob/caf3e8f6a3a82af83114d3b58a41dcb3a51a0540/README.md), [Windows-Build-Anleitung](https://github.com/mapillary/OpenSfM/blob/caf3e8f6a3a82af83114d3b58a41dcb3a51a0540/doc/source/building.rst), [CPU-Dense und merged.ply](https://github.com/mapillary/OpenSfM/blob/caf3e8f6a3a82af83114d3b58a41dcb3a51a0540/opensfm/dense.py), [C++-Depthmap-Rechnung](https://github.com/mapillary/OpenSfM/blob/caf3e8f6a3a82af83114d3b58a41dcb3a51a0540/opensfm/src/dense/src/depthmap.cc), [OpenMVS-Export](https://github.com/mapillary/OpenSfM/blob/caf3e8f6a3a82af83114d3b58a41dcb3a51a0540/opensfm/actions/export_openmvs.py).

## Dokumentierte Standardkette und wichtige Windows-Lücke

Nach Metadaten → Merkmale → Bildabgleich → Tracks → Rekonstruktion folgen laut Dense-Dokumentation:

1. `undistort`
2. `dense_clustering`
3. `compute_depthmaps`
4. `fuse_depthmaps`
5. `dense_merging --georeferenced`

Die georeferenzierten `dsm.tif` und `ortho.tif` entstehen im letzten Schritt. Die vorhandene GeoTIFF-Prüfung und der vorhandene Import in SolarCheck bleiben die Datenschnittstelle; keine neue Orthoprojektion oder eigener Importer.

**Das mitgelieferte `bin/opensfm_run_all.bat` nicht ungeprüft als vollständigen Orthofoto-Starter weitergeben.** Im geprüften Stand folgen auf `reconstruct` die Schritte `mesh`, `undistort`, `compute_depthmaps`. `dense_clustering`, `fuse_depthmaps` und `dense_merging --georeferenced` fehlen. Die Aktion `compute_depthmaps` verlangt ausdrücklich die zuvor gespeicherten Cluster. Ein späterer dünner SolarCheck-Adapter müsste die dokumentierten vorhandenen CLI-Stufen vollständig aufrufen und ihre Ergebnisse prüfen, statt diese BAT unverändert zu delegieren. Dies ist ein festgestellter Skript-/Dokumentationsunterschied, noch kein lokal ausgeführter Fehler.

## Konkreter nächster Schritt

Die [lokale OpenCL-Prüfung](OPENSFM_OPENCL_WINDOWS10.md) ist jetzt als einzelnes Standardbibliotheks-Skript vorbereitet. Hardware-/OpenSfM-Abnahme beim Nutzer steht aus.

Zuerst den eigenständigen Build und OpenCL unter Windows 10 isoliert qualifizieren: separate Werkzeugumgebung, keine Änderung an vorhandener SolarCheck-Python-Umgebung, SQLite, Originalen oder gestoppten Pilotjobs. Werkzeug-/Kernelstart und vollständige Standardstufen zunächst ohne Kundendaten prüfen. Keine automatische Installation, keine Paket-/Engine-Integration in diesem Prüfblock.

Erst danach einen bewusst lokal gestarteten Pilot mit einer vollständigen zusammengehörigen RGB-Serie, bestehenden Metadaten und privaten Arbeitskopien vorsehen. Quelle/Build, registrierte Bilder, Abdeckung, scharfe PV-Kanten, echte GeoTIFF-Referenz und Laufzeit festhalten. Teilmodelle nicht als Gesamtorthofoto übernehmen. Anschließend gemeinsames RGB-/Thermal-Raster und Werteerhalt gesondert qualifizieren. Keine erneuten COLMAP-/MicMac-Blindläufe, keine eigene Engine.

Der vorhandene OpenSfM-Export `export_openmvs` ist im Quellcode belegt. Er wäre eine mögliche separate Sparse→OpenMVS-Schnittstelle, falls die native OpenCL-Kette nicht passt; vorhandenes OpenMVS-CPU und GeoTIFF-Formatadapter könnten dann weiterverwendet werden. Diese Kombination ist **nicht implementiert oder praktisch validiert** und wird nicht gleichzeitig als weiterer Pilot gestartet. Der Export allein belegt keinen metrischen CRS-Transform oder vollständigen Kameraverbund.

## Unabhängiger RGB-/Thermal-Referenzvergleich

Der Nutzer hat ein passendes RGB-/Thermal-Dateipaar namentlich bestätigt. Die gezielt geladene Thermal-Drive-Vorschau zeigt links ein zusammenhängend erkennbares Dach, rechts starke Verziehungen/Fragmente/Lücken. Das RGB ist inzwischen über den Ordnerlink gefunden; Drive-Thumbnail liefert HTTP 404, daher **noch kein visueller RGB-/Thermal-Vergleich**. Kein weiterer Dateilink erforderlich. Original-TIFF, CRS/Transform, Pixelwerte, Auflösung und gegenseitige Registrierung sind ungeprüft. Linkes Dach nur visueller Testkandidat, rechter Fehlerbereich nicht auswerten. Beschneiden ersetzt keine Geometriekorrektur. Keine privaten Dateinamen, Drive-IDs, Kundenbilder/-pfade, Koordinaten oder Vorschauen ins Repository übernehmen.

## Primärquellen

- [Release v1.1 und Thermal-Fix](https://github.com/OpenSfM/OpenSfM/releases/tag/v1.1), [Quellstand v1.1](https://github.com/OpenSfM/OpenSfM/tree/8b6b77efddebf4429044d3206c7dc21c4e767e08).
- [README und Funktionsumfang](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/README.md), [BSD-Lizenz](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/LICENSE).
- [Windows-Build](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/doc/building.md), [Conda-CI-Matrix](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/.github/workflows/conda.yml).
- [Dense-/GeoTIFF-Kette und GPU-Voraussetzung](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/doc/dense.md), [Georeferenzierung](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/doc/georeferencing.md).
- [GPU-Geräteauswahl](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/opensfm/dense/depthmaps.py), [Konfiguration](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/opensfm/config.py).
- [Windows-Gesamtskript](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/bin/opensfm_run_all.bat), [Cluster-Voraussetzung](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/opensfm/actions/compute_depthmaps.py), [GeoTIFF-Abschlussaktion](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/opensfm/actions/dense_merging.py).
- [Vorhandener OpenMVS-Export](https://github.com/OpenSfM/OpenSfM/blob/df1fbb56b2ac387e909003d852761a5bbd0ee619/opensfm/actions/export_openmvs.py).
