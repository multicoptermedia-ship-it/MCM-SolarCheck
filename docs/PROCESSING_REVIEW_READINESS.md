# Verarbeitung vor Fachprüfung – verbindliche Zielregel

Stand: 23.10.2026. Entwicklungsbranch: `feature/offline-human-report-approval`.

## Beobachtung im echten Windows-10-Pilot

Im separat gestarteten Projekt SC-0003 wurden **160 Thermalbilder, 33 RGB-Bilder und 33 rein metadatenbasierte Paare** importiert. Beim Thermalimport wurden automatisch **16.000 ungeprüfte Rohkandidaten** gespeichert, obwohl **0 PV-Module** vorhanden waren. Die bisherige Workflow-Ableitung wertet `summary.findings > 0` bereits als Voraussetzung für die Fachprüfung. **Das ist KEIN belegter vollständiger Verarbeitungsabschluss** und für den gewünschten Benutzerablauf unzureichend.

## Zielablauf

1. Original-DJI-Flugordner importieren; optional fehlende Bildgegenstücke nachladen; originale Bytefolgen unangetastet lassen.
2. Vollständige Verarbeitung als eigenen, wiederanlaufbaren, abbrechbaren Projektauftrag starten. Dateianzahl, Einzelbilder, Batch-/Segmentstatus, Fehl- und Teilresultate sowie die tatsächlich verwendeten Pipeline-/Modellversionen erfassen. Ergebnisse bleiben vorerst unbestätigte Vorschläge.
3. Erst **nach belegtem erfolgreichen Abschluss aller verpflichtenden Verarbeitungsschritte für den aktuellen Datensatz** die fachlichen Einzelentscheidungen freischalten. Fehlschlag, Abbruch, Teilresultate, veränderte/neu importierte Eingaben oder alte Abschlussmarkierungen müssen die Freigabe verhindern.
4. Fachkundiger Prüfer entscheidet je Kandidat ausdrücklich. Kundenbericht und Export benötigen weiterhin getrennte bestehende Freigaben.

### Implementierte Grundlage vom 24.10.2026

- `offline_processing_inventory.py` berechnet einen projektspezifischen SHA-256-Fingerabdruck ausschließlich aus **gespeicherten SQLite-Eingaben** (RGB-/Thermalframes, Paare, vorhandene private Importprüfsummen). Kein Einlesen privater Fotos, keine Pfade im GUI oder in Logs. Die echte Dateiintegrität ist dadurch **nicht** erneut geprüft und bleibt eine eigene Voraussetzung des künftigen Workers.
- Datenbankschema 21 legt `offline_processing_runs` an (projektbezogener Lauf, unveränderlicher Eingabe-Fingerabdruck, verpflichtende Thermalanzahl, Pipeline-Version, Laufzustand und Fehler-/Fortschrittszahlen). V20-Migration fügt **keinen** fiktiven erfolgreichen Alt-Lauf hinzu.
- Der Service kann einen Lauf atomar beginnen sowie Fehlschlag oder Abbruch speichern; parallele aktive Läufe desselben Projekts sind ausgeschlossen. **Es gibt noch keine API, einen Lauf als vollständig erfolgreich zu markieren.**
- Die Windows-Verarbeitungsseite zeigt den tatsächlich vorhandenen Laufstatus und warnt vor geändertem Input. Alle Statusmeldungen bleiben ausdrücklich unterhalb einer fachlichen Review-Freigabe.
- Tests prüfen projektspezifische Daten, Fingerabdruck bei Nachimport, Doppelstart, ungültige Statusübergänge, Abbruch, v20-Migration und Qt-Hinweise. CI dieser neuen Runde bei Erstellung noch offen.
- **Keine sichere Review-Sperre behaupten:** `WorkflowAction.REVIEW` wertet zurzeit weiterhin importierte Kandidaten als Verarbeitungsbeleg. Backend-Koppelung an einen vom zukünftigen Worker geprüften Abschluss ist noch ausdrücklich ausstehend. Erst dann reale Nutzerdaten fachlich prüfen.

### Nötiger technischer Abschlussnachweis – noch nicht implementiert

- Dauerhafter, projektspezifischer Verarbeitungsauftrag mit unveränderlicher Eingabeinventar-/Versionssignatur.
- Vollständigkeitsnachweis der verarbeiteten Quelldateien und zugelassenen fehlenden Gegenstücke; Null Befunde ist ein möglicher valider Analyseausgang und darf nicht automatisch als fehlende Verarbeitung gelten.
- Unveränderliche erfolgreiche Endmarkierung erst **nach** Commit der überprüften Ausgaben. `findings`, `pv_modules`, Paarungszahl oder Klicks allein sind keine Nachweise.
- Backend-Guard für `WorkflowAction.REVIEW` **und sämtliche entscheidungsschreibenden APIs**. GUI allein ist kein Sicherheitsschutz. Separate Report- und Exportgates müssen denselben Stand respektieren.
- Migration älterer Projekte: niemals alten Import automatisch als `completed` nachtragen, aber vorhandene revisionssichere Fachentscheidungen und Berichtfreigaben nicht stillschweigend löschen.
- Regressionsfälle: vor Verarbeitung, nach Abbruch, nach Teilerfolg, nach verändertem Import, projektspezifisch, stale GUI callbacks, nach Neustart, alter DB-Stand, manipulierte Endmarkierung.

## Gegenwärtige, tatsächlich implementierte Zwischenstufe

Die Windows-Verarbeitungsseite zeigt jetzt **kompakte importierte Kennzahlen**, eine ausdrücklich **nicht nachgewiesene Verarbeitung**, einen verständlichen Ablauf und bei Bedarf ausklappbare technische Detailwerte. Sie hat einen Scrollbereich für Windows 10 und zeigt bei nummerierten Projekten die Anzeige `SC-xxxx · Anlagenname`.

Der existierende Workflow-Guard lässt Review derzeit noch anhand gespeicherter Findings/Module zu; **diese fachliche Lücke ist offen**. Die aktuell entwickelten Qt-Änderungen dürfen deshalb nicht als vollständige Review-Sperre bezeichnet werden. Bis der Abschlussnachweis und der Backend-Guard implementiert und getestet sind, sind echte Fachentscheidungen mit unvollständig verarbeiteten Pilotdaten zu unterlassen.

Kein Commit echter Kundendaten, GPS, Bildpfade oder DJI-Originalbilder nach GitHub. Kein Merge nach `main` ohne ausdrückliche Freigabe.


## Bilddateiprüfung als nächste sichere Teilstufe (24.10.2026)

- `services/offline_imported_image_check.py` prüft alle aktuell eingetragenen RGB- und Thermaldateien **lesend**, mit Byte-Limit je Datei, SHA-256-Abgleich wo ein Import-Hash existiert, PIL-Dateistrukturprüfung, Projektinventar-Vorher/Nachher-Vergleich und Abbruchprüfung pro Leseblock. Private Pfade/Dateinamen werden weder im Ergebnis noch in der Oberfläche ausgegeben. Eine Datei ohne Import-Hash ist **nicht** als identisch zum Import bestätigt.
- `gui/offline_imported_image_check_worker.py` führt diese Arbeit in einem Qt-Thread aus, meldet ausschließlich aggregierte Zahlen; GUI zeigt Fortschritt, Abbruch und generische Fehler. Quelle sind nur bereits importierte Pfade. `gui/shell.py` verwirft veraltete Projektsignale und hält Threads beim Programmende am Leben, bis sie beendet sind.
- Button **„Importierte Originalbilder prüfen (nur lesend)“** ist ausschließlich eine **VORPRÜFUNG** und **kein** vollständiger Verarbeitungsstart, keine Defekt-/Modulanalyse, keine RGB/Thermal-Pixelregistrierung, keine Kalibrierung, keine Berichts-/Reviewfreigabe. Projekt-Laufjournal `offline_processing_runs` bleibt von der Vorprüfung unverändert.
- Neue synthetische Tests: `tests/test_offline_imported_image_check.py`, `tests/test_gui_imported_image_check.py`; echte Kundenbilder bleiben nur auf dem Nutzerrechner. Alle aktuellen CI-Ergebnisse vor neuem Windows-Praxistest prüfen. Für die neue Programmversion zwingend erst **neue separate Kopie** von Code und Testdatenbank wegen Schema v21 verwenden.
- Noch offen: sicherer vollständiger Verarbeitungslauf (verifizierte Bildintegrität, Modell-/Algorithmusstufen, Batch-/Dateistatus, Ergebniskonsistenz und atomarer Abschluss), erst danach zentrale Fachreview-Sperre. `WorkflowAction.REVIEW` ist derzeit für Rohkandidaten **zu permissiv**. Kein Merge zu `main`.


## DJI-MPO-Felderkenntnis und Korrektur (24.10.2026)

Der echte, ausschließlich lokal durchgeführte Windows-Pilot mit SC-0003 (160 Thermal-, 33 RGB-Bilder, 33 gespeicherte **Metadatenpaare**) zeigte zunächst „0/193 strukturell lesbar, 193 Probleme“. Eine **rein lesende** Diagnose an einem Thermal- und einem RGB-Bild ergab jeweils: Datei vorhanden, Pillow-Bildformat `MPO`, `Image.verify() == OK`, importierte SHA-256-Prüfsumme stimmt. Ursache im neuen Vorprüfcode: explizite Format-Whitelist enthielt nur `JPEG/PNG/TIFF`, nicht `MPO` (DJI-Dateien mit JPG-Endung können von Pillow als MPO erkannt werden). Kein Hinweis auf defekte Originale.

Korrektur: Whitelist um `MPO` ergänzt; Byte-/Dateigrößenlimits, originale Import-Prüfsummen, `verify()`, Stale-Input-Kontrolle, Unterbrechbarkeit und alle Review-/Report-Sperren unverändert. Regressionstests reproduzieren den konkreten `Image.format='MPO'`-Wert mit **synthetischen JPEG-Bytes** und sichern einen fehlerhaften Hash weiterhin ab. Es werden keine echten DJI-Bilddaten in GitHub hochgeladen.

**Weiterer Test:** neue isolierte ZIP-Version in frischem Verzeichnis installieren; bereits isolierte Testdatenbank `F:\\MCM-SolarCheck-Testdaten-ebb61e2\\solarcheck.sqlite3` nur nach Sicherung/CI-Prüfung verwenden. Vor dem Austausch aktuelle App vollständig schließen. Beim Test die 193 Dateien erneut prüfen und tatsächliche Zähler melden; Erfolg ist nicht vorwegzunehmen. Produktionsdatenbank `C:\\Users\\User\\MCM-SolarCheck\\solarcheck.sqlite3` und Originale bleiben unberührt. Auch bei „193/193“ keine abgeschlossene Solar-/PV-Analyse, Pixelregistrierung, Kalibrierung oder Review-Freigabe behaupten.


## 24.10.2026 – Offline-Fachprüfung jetzt standardmäßig gesperrt

- `offline/composition.py` aktiviert bei jedem echten Offline-Start explizit `require_verified_offline_processing=True` im `ProjectApplicationService`/`ProjectWorkflowService`. Der bisherige **gemeinsame** Workflow für separat konstruierte Anwendungen/Online-Produkte bleibt einstweilen unverändert; es erfolgt **keine** globale Migration oder automatische Freigabe.
- `services/offline_review_gate.py` sperrt Review, Berichtsvorbereitung und Export bei fehlendem, noch laufendem, fehlgeschlagenem, abgebrochenem, veraltetem oder nur als `completed` markiertem Lauf. Letzteres ist absichtlich weiterhin gesperrt, weil es **noch keinen echten Worker und keinen unabhängigen Output-Integritätsnachweis** gibt. Rohbefunde, PV-Modul-Zahlen und der erfolgreiche 193/193-Datei-Check sind explizit **kein** Nachweis vollständiger Bildverarbeitung.
- Alle zentralen Backend-Schreiboperationen zur Fachprüfung verwenden `service.require(..., WorkflowAction.REVIEW)`, die Offline-Produktinstanz benutzt jetzt die strenge `service.state(...)`-Ableitung. Dadurch sperrt die Qt-Navigation den Review-Bereich ebenfalls. Historische Review-Audit-Einträge und Freigabehistorien bleiben gespeichert, werden nicht gelöscht oder auf `completed` gesetzt.
- Neue Tests: `test_offline_review_requires_processing.py` für Projektisolation, Status, manipuliertes `completed`, veränderte Eingaben, API-Schreibzugriffe, Historienerhalt; `test_gui_offline_review_full_processing_gate.py` für echte Offline-Qt-Navigation, gesperrten Review-Button und stale callback. Begründungen erscheinen auf Deutsch.
- Es gibt weiterhin **noch keinen tatsächlich erfolgreichen, prüfbar persistierten vollständigen Verarbeitungsjob**. Die Schutzsperre ist deshalb absichtlich streng und verhindert reale neue Fachentscheidungen bis zur späteren Implementierung. Prüfung der Windows-/Ubuntu-CI vor jeder neuen Test-Installation. Bei Tests, die absichtlich bereits früher existierende Reviewer-Interaktionen simulieren, darf ausschließlich testseitiges Mocking der *künftigen* Abschlussprüfung genutzt werden; nie ein Bypass in der ausgelieferten Desktop-Komposition.
- Lokale Pilotversion `F:\\MCM-SolarCheck-20add5b8222459c2c386c4c5df2bac62c4ba5a01` wurde vom Benutzer **geschlossen**. Vorher ergab die lesende Prüfung in `F:\\MCM-SolarCheck-Testdaten-ebb61e2\\solarcheck.sqlite3` **193/193 lesbar, 193/193 gespeicherte SHA-256-Hashes übereinstimmend, 0 Probleme**. Dabei weiterhin nur **33 Metadatenpaare**, keine überprüfte geometrische Überlagerung, 16.000 ungeprüfte Rohkandidaten. Keine lokalen Dateien geändert. `main` bleibt unberührt.


## 24.10.2026 – Nächste technische Vorstufe: echte 16-Bit-Thermalrohwerte

Der Windows-Pilot mit 193 von 193 lesbaren JPG/MPO-Dateien bestätigte die
Dateiintegrität, aber **nicht** die Nutzbarkeit der radiometrischen Rohdaten.
Eine davon unabhängige, ausschließlich **lesende** technische Prüfstufe ist
jetzt als eigener Entwicklungsabschnitt implementiert:

- `services/offline_thermal_raw_check.py`: alle ausgewählten Projekt-Thermalbilder
  mit maximal 120 MB pro Datei chunkweise lesen, gespeicherte
  Import-SHA-256-Prüfsumme vergleichen, die strukturellen APP3/APP4/APP5-Blöcke
  und vollständigen 640×512-16-Bit-Rohwerte mittels des vorhandenen
  M3T-Parsers dekodieren, gespeicherte Rasterabmessungen abgleichen.
- Abbruch zwischen Datei-Chunks, projektspezifischer Fortschritt,
  gesonderte Zähler für authentisierte Rohdaten, fehlende Prüfsummen und
  fehlerhafte Daten, Fingerabdruckvergleich der Eingabeinventare vor/nachher.
  Es werden keine Dateipfade, DJI-Originalbytes oder Koordinaten angezeigt.
- Separater Qt-Hintergrundthread, Projektwechsel-/Schließschutz und zweite
  Schaltfläche `Thermal-Rohdaten prüfen (nur lesend)` auf `Verarbeitung`.
  Die erste JPEG/MPO-Dateiprüfung und die neue Rohdatenprüfung schließen
  sich gegenseitig aus; beide ändern **weder** Originaldateien noch DB,
  Findings, Reviews, Berichte oder Verarbeitungsstatus.
- Erfolgreich dekodierte Rohwerte sind **keine Temperaturangaben in °C**,
  keine PV-Modulsegmentierung, keine qualifizierte Anomaliediagnose,
  keine RGB/Thermal-Pixelüberlagerung und vor allem **kein vollständiger
  Verarbeitungsabschluss**. Review, Bericht und Export bleiben gesperrt.
- Synthetische Tests decken SHA-Änderungen, fehlende Prüfsummen,
  unlesbare APP-Ketten, Dimensionsfehler, Größenbegrenzung, Abbruch,
  geänderte Projekteingaben und den echten Qt-Arbeitsablauf ab.
  Keine echten DJI-Bilder, Pfade oder Kundendaten werden nach GitHub übertragen.
- Die bereits bestehende Tabelle `offline_processing_runs` bleibt
  bei dieser Teilstufe absichtlich leer, damit noch kein Verarbeitungslauf
  fälschlich abgeschlossen erscheint. Für den späteren vollständigen Worker
  sind nachvollziehbare, persistierte Einzelbild-/Phasenstände separat zu
  implementieren. Vor einem neuen Windows-Einsatz alle vier CI-Prüfungen
  bestätigen und nur die vollständig isolierte Testumgebung verwenden.


## 24.10.2026 – Bildweise Thermal-Sensorstatistik als nächste echte Teilanalyse

- Nach erfolgreichem Windows-Pilot (160 von 160 echte DJI-Rohbildströme dekodierbar) rechnet die neue `services/offline_thermal_statistics.py` für jedes einzelne **SHA-256-bestätigte** Thermalraster die realen Sensorrohwert-Kennzahlen (Minimum, Maximum, Mittelwert, Median, Perzentile, Dynamik) mittels `thermal.analysis.raw_statistics`. Es handelt sich **nicht um Celsius-Temperaturen**. Wenn der gespeicherte Import-Hash fehlt oder nicht stimmt, wird keine Statistik für dieses Bild berechnet.
- Die Auswertung bleibt im Arbeitsspeicher und gibt an die GUI nur Zähler, projektweite Sensorrohwert-Extremwerte und Anzahlen konstanter bzw. variabler Bilder zurück. Weder Bildinhalte noch Dateipfade, GPS-Daten oder Einzelbildstatistiken werden an die GUI oder GitHub ausgegeben. Nach jedem Bild wird das dekodierte Raster verworfen.
- Eine dritte Schaltfläche auf der Seite `Verarbeitung`: **„Thermal-Sensorrohwerte statistisch auswerten (nur lesend)“**; Qt-Hintergrundthread mit Fortschritt, Abbruch und Schutz vor parallelen Prüfungen, Projektwechsel und Programmende.
- Das bestehende `offline_processing_runs`-Journal wird **nicht** verändert. Es gibt keinen fingierten Verarbeitungsabschluss. Fachprüfung, Bericht und Export bleiben gesperrt, auch wenn alle Rohstatistiken berechnet werden konnten. Noch fehlen insbesondere verifizierte RGB/Thermal-Pixelregistrierung, PV-Modulsegmentierung, Kalibrierung, Expertenkontext und persistierter atomarer Vollständigkeitsnachweis.
- Synthetische Tests sichern echte Statistikberechnung, konstante Rohwerte, Hash-Mismatch, fehlenden Hash, beschädigte bzw. fehlende Quelldatei, Größenlimit, Abbruch, Projektänderung und Qt-Gates ab. Vor Windows-Test **alle vier** CI-Jobs auf dem neuen Commit kontrollieren. Produktionsinstallation und DJI-Originale nie ändern.
