# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md), [Anforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) und [GeoTIFF-Ablauf](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md) lesen. Neueste Nutzeranweisung hat Vorrang.**

## Auftrag und Grenzen
Ziel bleiben **ein RGB-Orthofoto und ein Thermal-Orthofoto**, georeferenziert als2D-GeoTIFF, danach automatische PV-Erkennung/Modulzuordnung/Thermalanalyse/Review/Bericht. **Windows 10**, Offline zuerst/Online später mit gemeinsamem Fachkern. Repository multicoptermedia-ship-it/MCM-SolarCheck, Feature-Branch feature/orthofoto-license-neutral-rgb-first-20261028, Draft **PR #9**, **kein Merge/Push nach main**. main bleibt5f2de8fa; SolarCheck2 unverändert.
**DEV-RGB-ORTHO-ENGINE-001: 3D-Entwicklung bis auf Weiteres einfrieren.** Eigene Photogrammetrie bleibt **eingefroren**, **keine neue Photogrammetrie-Engine**/SfM/BA/Stitchentwicklung. Keine ODM/WebODM/ODX-Integration/Prozesse/APIs/Container/Installer. Nutzer darf WebODM unabhängig manuell betreiben. MicMac nach zwei realen Fehlschlägen und COLMAP/OpenMVS nach287er Fortsetzung ohne Einzelmodell zurückgestellt. Keine neuen Matching-/SfM-/Dense-/RGB-Läufe, Originalinventuren oder Setup-/Compiler-/SDK-/GPU-/Cleanup-Diagnosen. Bestehende F:-Python/SQLite/ZIP-Start-/OpenSfM-/QGIS-Umgebungen erhalten.
Kundendaten/EXIF/GPS/RTK/private Raster/SQLite/Backups bleiben lokal, Originale read-only. Codex nur Repository-Code/synthetische Tests sowie ausdrücklich angeforderte öffentliche PVIS-Forschungsdaten, keine privaten Bilder lesen/exportieren/trainieren. Nutzer installiert lokal selbst; vorhandene Piloten freigegeben, keine neue Freigabefrage. Keine proprietäre/kostenpflichtige Orthofotosoftware. Daten-/Code-/Gewichtsrechte getrennt prüfen, keine Produktionsfreigabe.

## Vorhanden und real bestätigt
- GeoTIFF/GIS-Prüfung, atomarer Paarimport/Schema22, Übersicht/Overlay/Zoom/PV-/Review-/Berichtskern vorhanden; wiederverwenden. VERT-01 fachlich offen.
- RGB real PASS13.11.:287Bilder, gespeichertes undistorted/depthmaps/ortho.tif laut Nutzer sauber; nicht neu rechnen. Unabhängige Geometrieabnahme offen.
- THERMAL-BASE-01:16-Bit-Rohsensorparser/Statistik/Anomalievorschläge und mittiger Kontrollmesspunkt vorhanden; keine neue Inventur. Pixel-°C-Provider Stub, keine volle Konvertierung. [Bestandsprüfung](THERMAL_PRUEFSTAND_2026-11-13.md).
- Thermal-Teilvorschau real technisch PASS:280/287 im Hauptmodell/sieben ausgeschlossen, Zusatzabgleich ausgeschöpft, fünf Folgestufen fertig. Dauerlabel **unvollständig: 280 von 287 Bildern**, auch GeoTIFF-Tags. Regulärer RGB-/Thermal-Paarimport gesperrt, auch umbenannt/kopiert. Quellen/eigene gespeicherte Thermalposen/Ausschlussnachweis erhalten. failed/595,094s/0raw/0clean ist Kameralaufhistorie13.11., keine Vorschauzeit/Freigabe.
- RGB-/Thermal-Sichtvergleich und PV-Entwürfe/Korrektur/Löschen/Zoom/Speichern/Wiederöffnung begrenzt real PASS. IDs nur jeAusschnitt, keine physischen IDs/Gesamtquote; Quellen/Notizen/Historie erhalten.

## Automatische Erkennung: Prüfstand
Automatische Modul-/Befundanalyse mit manueller Handlung nur bei unklaren Fällen; keine1000Pflichtfreigaben. Konfidenz keine Genauigkeitsgarantie, fehlende Module nicht gesund. Bestehender lokaler Modellvergleich/ROI/GIS/Abbruch/separate Berichte erhalten.
PV-Hawk-Feldqualität21→18Vorschläge/3von8Teilreferenzen, CVUT73/0von8 unzureichend. Bisherige Berichte/Modelle erhalten. Original-CVUT-Profil/Gewichtsrechte offen; keine unveränderten Wiederholungen. Vorhandene E:-Torch2.15CPU-/GPL3-Referenz21d7850f weiterverwenden.

## Aktiver Block27.11.: CVUT-YOLO-PUBLIC-01
**Ausgang geschlossen:** alter öffentlicher Pilot/Instanzprüfung real Windows10 technisch PASS, nicht wiederholen. Kontrollierter U-Net-Lernweg055cce62, letzte exakte CI Windows46022660820(216Paketfälle/Version,Torch18/PV-Hawk19), Linux46022660886/46022649848(4824PASS/90SKIP je3.11/3.12). Rune99de291…d3936/608Updates fachlich FAIL. Alte Trainer-/Adapter-/Ladedateien und Läufe erhalten.

**Zugriff gelöst:** öffentliches Nutzerpaket tatsächlich PV_module_segmentation_dataset.zip/699176611Bytes. ZIP-Verzeichnis und ausgewählte RGB-YOLOv8n/-s-Gewichts-/args-Mitglieder gelesen; keine CVUT-Bilder. n6806691Bytes/SHAe464ffde55d91727b19c8690706d79b70a3deb2398d7d564bb7a0a2656fea6e6; s23896931Bytes/SHA549c6d78…99674f. CRC/beobachtete Mitglied-SHA, kein Anbieter-/Gesamtarchiv-SHA. Keine erneute Linkfrage; persönlichen Drive-Link niemals veröffentlichen.

**Technik:** Ultralytics8.1.29/Klasse0module/Segmentierung/640Pixel/200Epochen/AGPL3. weights_only-Lader mit passiven Fremdklassen/begrenztem getattr; keine serialisierte Modellmethode.417primitive CPU-Tensoren, neues Standardmodell strict geladen. Eigene Cloud-Umgebung Torch2.15CPU/torchvision0.29.2CPU; alte App-/Torch-/PV-Hawk-Umgebungen erhalten. Keine Nutzerinstallation. PVIS-DatenCCBY4.0 und Code-/GewichtsrechteAGPL3 getrennt; Produkt-/kommerzielle Entscheidung unreviewed.

**Öffentliche Versuche abgeschlossen:** feste24Validierungscrops033/117Referenzbeobachtungen, keine eindeutigen physischen Module. Vortrainiert n640:28Treffer/441zusätzliche/89fehlend; n320:41/377/76; s640:34/297/83. Mehrstufige begrenzte Anpassung mit konservativen bekannten Ankern/Maskenpixeln, exakt null direktem Ignore-Gradient, eingefrorenen BatchNorm-Statistiken/-Parametern und DFL-Projektion. Weitere räumliche512→256-Kontexte und zwei öffentliche Trainingsanlagen018/029 nach vollständiger Anbieter-SHA-Prüfung im RAM, nur numerische ausgewählte Ausschnitte gespeichert. Keine großen ZIPs entpackt/gespeichert.009/018/029 je20Bilder,80/75/77Crops mit250/291/293Beobachtungen. Validierung033unverändert,024nie gelesen.

Letzter Versuch zehn Epochen/2320AdamW-Updates/Lernrate0,00003, Auswahl Epoche8 nach Rohmasken-F1: **90Treffer/129zusätzliche/27fehlend**, Rohflächen-IoU0,89024. Nach vollständigen Rechteckumrissen/Füllung/Geometrie/Dublettenprüfung: **59Treffer/45zusätzliche/58fehlend**. Fachlich ungeeignet für automatische Anlagenzählung; viele Anpassungen an derselben033-Validierung, keine unabhängige allgemeine Genauigkeit. Keine GUI-Modellübernahme/Produktfreigabe.

**Gesichert:** scripts/MCM_SolarCheck_CVUT_YOLO_PRUEFUNG.py prüft veröffentlichte n-Gewichte oder SHA-gebundenen Tensor-Kandidaten am vorhandenen öffentlichen Korpus, ohne Training/Download/Installer. Eigenes neues Ergebnis; Abbruch veröffentlicht nichts; --show liest fertiges JSON ohne Torch/Modell. Befunde und historische Cloud-Versuchsquellen unter docs/evidence/cvut-yolo-public-2026-11-27*. Kein fertiger Windows-Nutzertrainer oder behaupteter Trainings-Resume. Kandidatd80be7a0…cdc27 separat erhalten. Frühere ONNX-Probe technisch OpenCV-geprüft, anderes Vorläufergewicht; keine App-Zulassung. 71neue synthetische Vertragsfälle+7echte CPU-Referenzfälle grün; --show im App-Python identisch. Neue exakte HEAD-CI separat belegen.

**Nächster Einstieg:** [CVUT-YOLO-Befund](CVUT_YOLO_PUBLIC_REVIEW.md). Vollständige Modulgrenzen auf öffentlichen Daten verbessern, zunächst nativen Bildmaßstab/Modultrennung prüfen. Kein unveränderter Nutzerlauf/Installationsauftrag, keine1000Pflichtreviews. Erst tragfähigen Kandidaten einfrieren und separat an ungenutzten Daten prüfen;024bis dahin reserviert. Danach eigener ROI-/ONNX-Bericht und gezielte Windows10-Abnahme. PVIS-Projektionsflächen nicht mit privaten sichtbaren Eckenumrissen mischen. Kunden/SQLite/Geotags lokal; Quellen/eigene Thermalposen/Label280/287/Paarimport-Sperre/Fachflagsfalse erhalten.

## Übergabe und Abnahme
Vor Chatende Checkpoint(1000–8500Zeichen), Register/Vereinbarung/Handoff/Roadmap aktualisieren; exakte HEAD-CI in PR9 prüfen. Technische Tests/Quellenprüfung/reale Abnahme trennen. Ziel: beide GeoTIFFs/scharfe Module/unabhängige Geometrie/Thermalzuordnung. Danach VERT-02/Befund→Modul→RGB→Entscheidung→Bericht; Online/Installer später.


Instanzprüfquellea5cca60d/ZIP3290858Bytes/SHA804e6b65d21a8083898911949dc4c9330b5645b23bbd88e56726e105c3abba6e;700Runtime-Dateien+9Konfig/Paketlisten remote bytegleich. Trainer-/Adapterquellen825cd57d/29b651c2 erhalten.

CVUT-YOLO-Prüfquelleac873071/ZIP3402970Bytes/SHA07e18b14d43513ade78cb2b535cb5cfe6e7734a4c0e21beca0164eacede3aea9;708Runtime-Dateien+10Konfig/Paketlisten remote bytegleich. Keine Nutzerinstallation oder unveränderte Erkennungswiederholung nötig.
