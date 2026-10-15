# MCM-SolarCheck – verbindliche Entwicklungsvereinbarung

Diese Datei ist der dauerhafte Übergabepunkt zwischen Chat-Sitzungen. Vor neuen Entwicklungsblöcken diese Datei, die aktuellen Branches/PRs und die jüngsten Commits prüfen. Bestehende frühere Anforderungen bleiben gültig; diese Datei ergänzt sie, statt sie zu ersetzen.

## Entwicklungsreihenfolge und Architektur
- Vertikale Entwicklung: eine Funktion entlang der gesamten nutzbaren Prozesskette integrieren (Import → Verarbeitung → Fachprüfung → Bericht/Export), statt unverbundene Teilsysteme zu bauen.
- **Offline zuerst.** Zuerst die lokale Windows-/Desktop-Anwendung und ihre fachliche Prozesskette fertigstellen und prüfen.
- Gemeinsam benötigte Logik gehört in den wiederverwendbaren Kern und wird anschließend von der Online-Version über passende Adapter genutzt; keine doppelte fachliche Implementierung.
- Online-spezifische Dienste dürfen Offline-Funktionen nicht von Internetzugang abhängig machen.
- Der aktuelle Arbeitsstand liegt auf Entwicklungs-/Integrationsbranches; `main` ist nicht automatisch die maßgebliche Codebasis. Vor jeder Änderung Branches und offene PRs kontrollieren.
- Offene PRs nicht ungeprüft mergen; bestehende Funktionalität erhalten.

## Nicht verhandelbare Qualitäts- und Sicherheitsgrenzen
- KI-Ergebnisse sind Vorschläge, keine automatisch bestätigten Diagnosen.
- Jeder echte KI-Befund wird zunächst als `pending` erfasst. Fachkundige Entscheidung und ausdrückliche Berichtsfreigabe sind erforderlich; ungeprüfte Vorschläge dürfen nicht in den Kundenbericht gelangen.
- Interne KI-Details (u. a. Modellkennung, Modellversion, Konfidenz, interne Eingabequellen und Prüfentscheidungs-Metadaten) bleiben aus Kundenberichten heraus, soweit nicht ausdrücklich freigegeben und fachlich erforderlich.
- RGB- und Thermalbilder im Bericht dürfen durch neue Änderungen nicht ausfallen; PDF-/ODT-/DOCX-Ausgabe und Bildnachweise regressionssicher behandeln.
- Herkunft, Nachvollziehbarkeit, Datenintegrität, Datenschutz, kundenseitige Einwilligungen und die Trennung zwischen KI-Vorschlag und Expertenurteil bewahren.
- Ziel: keine laufenden Modelllizenzgebühren; Modelle, Gewichte, Trainingsdaten und Abhängigkeiten vor kommerzieller Nutzung rechtlich prüfen. Keine ungeprüften Downloads, Lizenzzusagen oder Modellfreigaben.
- Normkonformität nicht ohne gültige Normprüfung behaupten; qualifizierte Fachprüfung bleibt erforderlich.
- Keine heimlichen Netzwerkübertragungen oder automatischen Kundenfreigaben.
- Python 3.11 und 3.12 sowie betroffene Regressionstests prüfen; niemals grüne CI-Läufe behaupten, wenn sie nicht bestätigt wurden.

## Arbeitsrhythmus: fünf Entwicklungsschritte je Runde
1. Pro Runde **fünf kleine, aufeinander aufbauende Schritte** planen und möglichst als nachvollziehbare einzelne Commits umsetzen.
2. Jeden Schritt auf der tatsächlichen aktuellen Codebasis durchführen, ohne funktionierende Teile neu zu erfinden.
3. Passende Sicherheits-, Funktions- und Regressionstests ergänzen.
4. Nach der Fünfer-Runde CI unter Python 3.11 und 3.12 abwarten bzw. den Nutzer um Bestätigung bitten. Ein Testlauf ist erst grün, wenn tatsächlich bestätigt.
5. Kurzen Übergabestand festhalten: Branch, Commits, erreichte Funktion, offene Risiken, nächster Fünferblock.

## Aktueller Übergabestand (13. Oktober 2026)
- Repository: `multicoptermedia-ship-it/MCM-SolarCheck`.
- Integrationspfad: PR #4 `feature/unified-online-offline-foundation` → `integration/phase10-master`; PR #3 `integration/phase10-master` → `main`. PRs nicht ohne Review mergen.
- Block 38: lokale KI-Ergebnisse werden als ungeprüfte Vorschläge gestaged; bestehende lokale Fachprüfung und Exportfreigabe sind vorhanden.
- Arbeitsbranch: `feature/block38-offline-ai-ingestion-tests`, abgeleitet von `feature/unified-online-offline-foundation`.
- Commits: `4e701976d5dea85a805f2a4864ffda368827d5fb` (KI-Importtests) und `e78b1cbfb3c0e8bdc53d4bafb882fce912aafbd4` (Offline-Review-/Export-Gates).
- Nutzer hat die letzten Testläufe als grün bestätigt. Diese Aussage ist eine Rückmeldung, keine eigenständige CI-Verifikation.
- Nächster Fokus: Block 38, echte lokale KI-Ergebnisse sicher an den bestehenden vertikalen Offline-Review-Workflow anbinden, ohne Freigabegates zu umgehen. Wiederverwendbare Fachlogik auch für Online nutzbar halten.

## Startanweisung für einen neuen Chat
`Bitte lies im Repository multicoptermedia-ship-it/MCM-SolarCheck die Datei docs/DEVELOPMENT_AGREEMENT.md auf dem aktuellen Entwicklungsbranch, prüfe Branches, PRs und letzte Commits und setze die Offline-first-Entwicklung in fünf getesteten Schritten fort. Alle bisherigen Vorgaben beibehalten.`

## Übergabe 15. Oktober 2026 – RGB-Stitch-Vorschau, Fünferblock
- Branch: `feature/block38-offline-ai-ingestion-tests`; `main` und offene PRs bleiben unangetastet.
- Vorheriger grüner CI-Lauf: `d24dc3e`, GitHub Actions Run 38763579957.
- Fünf Schritte dieser Runde: `bab6c3e` (Parametergrenzen), `1563f0b` (lokaler PNG-Export), `4450735` (sequenzielle RGB-Mehrbild-Vorschau), `1b60329` (Funktions-/Negativtests), dieser Dokumentationscommit.
- Die Mehrbildfunktion verwendet die bereits vorhandene ORB/RANSAC-Paarprüfung und begrenzt die Eingabe standardmäßig auf acht Bilder. Sie erzeugt ausschließlich eine **unverifizierte** lokale Vorschau, keine geometrisch geprüfte Orthofoto-Datei.
- Qualitätsrisiken: sequenzielles Stitching kann Drift erzeugen; Referenzbilder überdecken Überlappungsbereiche ohne Blending; kein Bundle Adjustment, keine Modulflächenentzerrung, keine unabhängige Coverage-Prüfung, keine RGB-/Thermal-Registrierung, keine radiometrische Temperaturfreigabe. PNG ist nur Vorschau, kein Berichtsnachweis einer Orthofotogenauigkeit.
- Die CI-Ergebnisse für diesen neuen Fünferblock sind noch **nicht bestätigt**. Python 3.11 und 3.12 prüfen, bevor der Block als grün gilt.
- Nächster Schwerpunkt nach grüner CI: realistische versetzte Bildausschnitte als Tests, geometrische Residuen und Coverage-Gates, robuste Multi-Frame-Registrierung und Desktop-Anbindung; bestehende Expertenfreigaben und Reportgates nicht umgehen.

## Übergabe 15. Oktober 2026 – geometrische Qualitätsgates, Fünferblock
- Voriger Fünferblock `bab6c3e` bis `b9b312c` wurde mit GitHub Actions Run 38764504820 grün bestätigt.
- Arbeitsbranch: `feature/block38-offline-ai-ingestion-tests`. Keine Merges nach `main` oder in Integrations-PRs.
- Fünf persistente Schritte: `8c8dcec` (pixelbasierte Canvas-Abdeckung, Schwarz zählt als gültiges Pixel), `1486780` (RANSAC-Inlier-Reprojektionsfehler als zusätzliches Fail-Closed-Gate), `d8077af` (Grenzen für transformierte Bildfläche), `a109cc8` (Negativ- und Coverage-Regressionstests), dieser Übergabecommit.
- Die Abdeckungskennzahl ist ausschließlich die Abdeckung der **Vorschau-Canvas**, nicht die Abdeckung einer PV-Anlage oder eines Fluggebiets. `verified_orthomosaic` bleibt immer `False`.
- Neue Gates sind heuristische Sicherheitsgrenzen, **kein** Nachweis photogrammetrischer Genauigkeit. Tests für tatsächlich versetzte Aufnahmen, Mehrbild-Drift und geometrische Referenzdaten stehen weiterhin aus.
- Aktuelle Runde: CI Python 3.11/3.12 noch **nicht bestätigt**. Bei Fehlern zuerst Workflow-Logs prüfen und gezielt korrigieren; keine stillschweigende Freigabe.
- Nächster Fünferblock nach grüner CI: synthetische Translationen mit echten gemeinsamen Bildmerkmalen, Residualmetadaten/Transform-Provenienz, Driftbegrenzung ohne wiederholtes Resampling, persistente Projektartefakte und sichere Offline-Desktop-Einbindung.
- Vorhandene Import-, KI-`pending`-, Expertenreview- und Bericht-/Exportgates bleiben unverändert. Kein Kundenbild wird an externe Dienste übertragen.

## Übergabe 15. Oktober 2026 – RGB-Registrierungsprovenienz, Fünferblock
- Branch: `feature/block38-offline-ai-ingestion-tests`; `main` und PRs unverändert. Voriger Qualitätsblock bis `df023ca` ist durch GitHub Actions Run 38765459779 grün bestätigt.
- Fünf Schritte dieser Runde: `5e04f87` (medianer Inlier-Reprojektionsfehler im Ergebnis), `b57004f` (synthetischer Test mit tatsächlich versetzten Ausschnitten), `c96aeca` (lokales JSON-Provenienzmanifest), `e3d7c81` (Manifest-/Pfadschutztests), dieser Dokumentationscommit.
- Ergebnisstatus bleibt ausdrücklich `unverified_preview` und `verified_orthomosaic=False`. Die gemessene Canvas-Abdeckung ist keine Fluggebiets-/Modulabdeckung. Das Residuum beschreibt nur den letzten verarbeiteten Bildpaar-Schritt, nicht eine globale Genauigkeitsprüfung.
- CI für **diese Runde noch nicht bestätigt**. Insbesondere den neuen Test mit verschobenen Ausschnitten unter Python 3.11 und 3.12 prüfen. Bei Rot zuerst Logs auswerten und Fehler beheben, nicht Gates abschwächen.
- Offene Kernaufgaben: Transformationen und per-frame Masken über alle Bilder aufbewahren; mehrfache Resampling-Schritte vermeiden; globale Drift prüfen; Metadaten und Vorschau als Projektartefakt in den echten Offline-Desktop-Workflow integrieren; Modulflächenentzerrung und georeferenzierte Orthofotoprüfung erst nach belastbaren Daten.
- Kundenbilder bleiben lokal; keine automatische Expertenfreigabe, keine ungesicherten Temperatur- oder Normkonformitätsbehauptungen.

## Übergabe 15. Oktober 2026 – lokale RGB-Vorschauartefakte, Fünferblock
- Arbeitsbranch: `feature/block38-offline-ai-ingestion-tests`; keine PR-Merges oder Änderungen an `main`.
- Voriger Block: JSON-Zeilenumbruchfehler behoben in `95b1552`; GitHub Actions Run 38766855323 erfolgreich.
- Fünf Schritte: `eac60d2` (nichtfinite Diagnostikwerte ablehnen), `7baa8b8` (lokales PNG+JSON-Artefaktpaar), `c996891` (Regressionstests für Artefaktpaar und ungültige Werte), `6d97629` (Validierung vor Dateioperationen), dieser Dokumentationscommit.
- Artefakte werden ausschließlich in einem bereits existierenden lokalen Verzeichnis geschrieben; vorhandene gleichnamige Dateien werden nicht überschrieben. Keine Online-Übertragung und keine automatische Expertenfreigabe. Fehler beim JSON-Schreiben führen zum Entfernen der zuvor geschriebenen PNG-Datei.
- Grenzen: noch keine Integration in die tatsächliche Desktop-Projektoberfläche, kein atomarer Zwei-Dateien-Commit, kein globaler Transformationsgraph, keine Driftkorrektur, keine Modulflächenentzerrung, keine georeferenzierte Orthofotoprüfung. Status bleibt `unverified_preview`.
- CI dieses neuen Fünferblocks noch nicht bestätigt; Python 3.11 und 3.12 abwarten, Fehler ggf. anhand der Logs beheben.
- Nächster Block nach grüner CI: bestehende Desktop-Projekt- und Import-APIs gezielt untersuchen, sicheren lokalen Aufrufpfad integrieren, danach per-frame Transformationsdaten/Masken und globale Driftprüfungen entwickeln. Bei jeder Runde wieder fünf Commits mit dauerhafter Übergabe.

## Übergabe 15. Oktober 2026 – vollständige RGB-Herkunft und Offline-Aufruf, Fünferblock
- Branch: `feature/block38-offline-ai-ingestion-tests`. Vorheriger Block bis `b707ffd`: alle fünf GitHub Actions Runs grün, letzter Run 38772547233. `main` und Integrations-PRs nicht geändert.
- Fünf Commits: `8058c23` (frame_count in Ergebnis/Manifest), `b561371` (Test für vollständige Herkunft und angepasste Negativtests), `9ce1180` (Herkunft vor PNG-Schreibzugriff prüfen), `678a12e` (lokaler Service-Aufruf `create_local_rgb_preview_artifacts` für Bilder → Vorschau → PNG+JSON), dieser Dokumentationscommit.
- Der neue Service-Aufruf ist ein **Application-Service-Einstiegspunkt**, noch keine angeschlossene Schaltfläche oder persistierte Projekt-Datenbankreferenz. Bestehende GUI `src/mcm_solarcheck/gui/project_page.py` ist projektlistenorientiert; Offline-Komposition `src/mcm_solarcheck/offline/composition.py` liefert `ProjectApplicationService`. Nächster Block soll an dieser tatsächlichen Struktur statt an erfundenen Projektpfaden ansetzen.
- Bekannte Grenzen: serielles Resampling und geometrische Drift, keine globale Transformation/Optimierung, keine Modulflächenentzerrung, keine Thermal-Registrierung, keine georeferenzierte Genauigkeitsprüfung. `verified_orthomosaic=False` und `unverified_preview` bleiben verbindlich; keine automatische Kundenberichtfreigabe.
- CI für diese fünf Commits ist **noch nicht bestätigt**. Python 3.11/3.12 prüfen; bei Fehlern Logs und Testursache bearbeiten.
- Nächste fünf Schritte: echten Desktop-Projektpfad/Medienablage ermitteln; Service-Aufruf dort ohne Blockierung der UI einhängen; Mehrbild-Transformationen pro Frame statt nur letzter Residuen erfassen; globale Driftgrenzen und Regressionstests; dauerhafte Übergabe.

## Verbindliche Ausgabevorgabe – georeferenzierte Orthofotos als GeoTIFF (15. Oktober 2026)
- Nutzeranforderung: Echte Orthofotos müssen für die Weiterverarbeitung in GIS-Programmen grundsätzlich als **GeoTIFF** bereitgestellt werden. **WebODM** ist als Referenz für photogrammetrische Verarbeitung und interoperable GIS-Ausgaben zu berücksichtigen, ohne ungeprüft eine identische Pipeline oder Genauigkeit zu behaupten.
- Ein GIS-taugliches Orthofoto braucht belastbare Georeferenzierung: dokumentiertes Koordinatenreferenzsystem (CRS/EPSG soweit bekannt), gültige Pixel-zu-Welt-Transformation, Pixelauflösung, räumliche Ausdehnung und NoData-/Alpha-Handhabung. Herkunft, Verarbeitungsstatus und Qualitätsnachweise müssen nachvollziehbar sein. Keine erfundenen Koordinaten, CRS oder Genauigkeiten.
- **Strikte Trennung:** Die vorhandenen PNG-/JSON-Stitch-Ergebnisse sind ausschließlich lokale, **nicht georeferenzierte, unverifizierte Vorschauen** (`verified_orthomosaic=False`). Sie dürfen weder in GeoTIFF umbenannt noch ohne echte räumliche Referenz als GIS-Orthofoto exportiert werden.
- Zielarchitektur: separater validierter GeoTIFF-Exportpfad für tatsächlich georeferenzierte Orthofotos; geeignete TIFF-/GeoTIFF-Metadaten und GIS-Interoperabilität automatisiert prüfen (z. B. lesbar in QGIS/GDAL), möglichst ohne verpflichtende Internetdienste. Gegebenenfalls WebODM-Exportformat und Metadaten bei der Implementierung vergleichen.
- Für geneigte PV-Modulflächen zusätzlich Ebenenentzerrung, geometrische Qualitätskontrollen und korrekte Zuordnung zum Weltkoordinatensystem beachten. GeoTIFF allein beweist weder Orthorektifizierung noch fachliche Genauigkeit.
- Vorhandene Expertenreview-, KI-`pending`-, Berichtsfreigabe- und Datenschutzregeln bleiben uneingeschränkt gültig.
