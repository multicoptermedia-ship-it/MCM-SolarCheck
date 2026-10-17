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

## Übergabe 15. Oktober 2026 – GeoTIFF-Referenzvertrag, Fünferblock
- Branch: `feature/block38-offline-ai-ingestion-tests`. Vorheriger Fehler im Test der RGB-Herkunft wurde in `9a0e294` behoben; GitHub Actions danach grün. `main` und PRs unverändert.
- Fünf Commits: `fe8f7c0` (GeoTIFF-Referenzvertrag mit CRS, Affintransformation, Rasterdimensionen, NoData und sicherem Ausgabeziel), `32abbab` (Gültigkeits-/Fehlertests), `0be4856` (Welteckpunkte aus affiner Transformation), `88cde76` (Tests für normale und rotierte Raster), dieser Dokumentationscommit.
- Die GeoTIFF-Prüfung validiert nur **bereitgestellte** Geometriedaten. Sie beweist weder deren Wahrheit noch Orthorektifizierung. Noch **kein GeoTIFF-Schreiber**, kein WebODM-Adapter, keine QGIS/GDAL-Leseprobe, keine Verbindung zur Desktop-Oberfläche.
- Verbindliches Ziel bleibt ein tatsächlich georeferenziertes GeoTIFF für GIS-Anwendungen. RGB-PNG/JSON bleibt ausdrücklich `unverified_preview`, ohne erfundene CRS oder Georeferenzierung.
- CI für den aktuellen Block noch **nicht bestätigt**; Python 3.11 und 3.12 prüfen. Bei Rot Logs analysieren und Fehler gezielt beheben.
- Nächster Fünferblock: echte Offline-Projektmedienpfade und Desktop-Aktionen ermitteln, vorhandene Raster-/GIS-Bibliotheken prüfen, tatsächlichen GeoTIFF-Export mit überprüfbarer CRS/Transform-Metadatenintegration erst auf Grundlage verifizierter Georeferenzdaten entwickeln; Regressionstests und Übergabe.

## Übergabe 15. Oktober 2026 – lokaler GeoTIFF-Schreiber, Fünferblock
- Branch: `feature/block38-offline-ai-ingestion-tests`; `main` und PRs nicht geändert. Voriger GeoTIFF-Vertragsblock bis `f18ce9a` mit GitHub Actions erfolgreich bestätigt.
- Fünf Commits: `69d3fe2` (lokaler GeoTIFF-RGB-Schreiber mit Rasterio, expliziter Freigabeparameter), `aa4d419` (GeoTIFF-Roundtrip für CRS, Affintransformation und RGB-Kanäle), `4e31e9a` (Teil-Dateien bei Schreibfehlern entfernen), `85df3c6` (Negativtests für Rasterform und Datentyp), dieser Übergabecommit.
- `requirements.txt` enthält bereits `rasterio>=1.4,<2` und `pyproj>=3.7,<4`; keine neue Cloud- oder Laufzeitabhängigkeit erforderlich.
- **Sicherheitsgrenze:** `write_georeferenced_rgb_geotiff` akzeptiert ausschließlich RGB uint8 HxWx3, validiertes CRS/Transform und `georeferencing_verified=True`. Dieser Parameter ist derzeit nur eine explizite Zusicherung des Aufrufers, **kein** kryptografischer oder photogrammetrischer Nachweis. Nicht mit den unverifizierten Stitch-PNGs verbinden. Der Export erzeugt eine GIS-georeferenzierte RGB-Rasterdatei, aber ohne echte Orthorektifizierung noch **kein fachlich bestätigtes Orthofoto**.
- Noch keine GUI-Integration, keine automatisch ermittelten Referenzdaten, keine geprüfte WebODM-Anbindung, keine belastbare Modulflächenentzerrung, keine globalen Genauigkeitsnachweise. Race-freies exklusives Erstellen und atomarer Export bleiben offen.
- CI für diesen neuen Block noch nicht bestätigt; Python 3.11/3.12 prüfen und bei Rot anhand der Logs korrigieren.
- Nächster Block: echte verifizierte Georeferenzierungsquelle und Offline-Projektanbindung identifizieren, GIS-Metadaten und NoData/Alpha-Interoperabilität ausbauen, robustes atomisches Schreiben und unabhängige Tests, danach Desktop-Integration mit Workflow-Gates.

## Übergabe 15. Oktober 2026 – GeoTIFF-Dateisicherheit und GIS-Importinspektion
- Branch `feature/block38-offline-ai-ingestion-tests`; letzter Block bis `754e96f` erfolgreich in GitHub Actions. Keine Änderungen an `main`, kein PR.
- Fünf Commits: `3f017fd` (lokal temporär schreiben und durch exklusiven Hardlink ohne Überschreiben veröffentlichen), `3ebda36` (Test zum Schutz bestehender Artefakte), `78f373a` (bestehendes GeoTIFF öffnen und CRS/Transform/Abmessungen lesen), `7ac0e26` (Roundtrip und fehlendes CRS testen), dieser Dokumentationscommit.
- **Wichtig:** `inspect_existing_geotiff` liest GIS-Metadaten, **genehmigt** keine Orthofotoqualität. Es gibt weiterhin keinen geprüften WebODM-Workflow, keinen echten photogrammetrischen Nachweis und keine automatische Georeferenzierung aus RGB-Stitch-Vorschauen.
- Writer nutzt `rasterio` und `os.link` zur exklusiven Veröffentlichung; Plattform-/Dateisystemverträglichkeit (Windows, Netzlaufwerke) und Crash-Dauerhaftigkeit müssen zusätzlich geprüft werden. Kein Überschreiben bestehender Kundendateien.
- Die Desktop-Projekt-/Medienpfad-Integration ist **noch offen**; diesen Punkt im nächsten Block priorisieren. Projektbezogene GIS-Importoberfläche darf nur inspizierte Metadaten anzeigen, nicht automatisch `georeferencing_verified=True` setzen.
- CI für diesen Block noch nicht bestätigt; Python 3.11/3.12 kontrollieren, Fehler korrigieren.
- Nächster Block: Offline-Projekt- und GUI-Einstiegspunkte konkret anbinden, separate Inspektionsaktion für bestehende GeoTIFFs anbieten, Windows-Pfade/Dateisysteme testen, Datenherkunft dokumentieren und echte GIS-Qualitätssicherung planen.

## Übergabe 15. Oktober 2026 – GeoTIFF-Metadatenprüfung in Desktop-Importseite
- Branch `feature/block38-offline-ai-ingestion-tests`; vorheriger Block bis `5fa16a9` laut GitHub Actions erfolgreich. `main` nicht verändert, kein PR.
- Commits: `0f9cc8a` (read-only `ProjectApplicationService.inspect_project_geotiff` mit Existenzprüfung), `6fe9334` (GeoTIFF-Dateiauswahl und Metadatenanzeige auf Importseite), `b3f06ca` (Shell-Anbindung mit Fehleranzeige und Projektwechsel-Reset), `5649c44` (GUI-/Projektisolationstests), `b45e763` (notwendige Qt-Offscreen-Testfixture), dieser Übergabecommit. **Ausnahmsweise sechs Commits**, weil die Testfixture nach dem ersten Testcommit ergänzt werden musste.
- Der Anwender kann im geöffneten Projekt unter „Bilddaten importieren“ eine lokale `.tif/.tiff` auswählen. Die Anwendung zeigt CRS, Pixelmaße, Transform und NoData. Keine Persistierung, keine Änderung von Workflow/Review-Status, keine Cloud. Fehlende/ungültige CRS führen zu einer Fehlermeldung. Das Vorhandensein von GIS-Metadaten ist **kein Nachweis** für korrekte Orthorektifizierung oder eine fachliche Freigabe.
- CI dieses Blocks noch nicht bestätigt. Insbesondere neue GUI-Tests und Windows-Qt prüfen und eventuelle Fehler beheben.
- Nächster Block: Desktop-E2E-Test mit realer Offline-Projektdatenbank und GeoTIFF; robuste Fehlermeldungen für Rasterio-Ausnahmen; nachvollziehbare GIS-Herkunft/Prüfprotokoll ohne automatische Freigabe; Windows-Pfadtests und tatsächliche Orthofoto-/WebODM-Qualitätssicherung.

## Übergabe 15. Oktober 2026 – echte Offline-Projekt-/GeoTIFF-Integrationstests
- Branch `feature/block38-offline-ai-ingestion-tests`; vorheriger Stand `f3d27a1` in GitHub Actions grün. Kein Merge/PR.
- Fünf Commits: `3294237` (beschädigte GeoTIFF-Dateien als kontrollierte Validierungsfehler), `f1ba75f` (Negativtest beschädigtes TIFF), `110ab44` (Desktop-E2E mit echter SQLite-Projektdatenbank und Rasterio-GeoTIFF), `620ec7c` (GUI-Fehlerfall und unveränderter Workflow), dieser Übergabecommit.
- Der E2E-Test baut `build_offline_services` mit echter SQLite-Datei, legt ein Projekt an, schreibt ein kleines synthetisches, ausdrücklich nur im Test als verifiziert gesetztes GeoTIFF und prüft CRS-Anzeige sowie unveränderten Projekt-Workflow. Er belegt **keine** echte photogrammetrische Orthorektifizierung oder WebODM-Ergebnisqualität.
- Noch offen: tatsächliche Herkunfts-/Prüfprotokoll-Persistenz, GIS-Datei als Projektartefakt referenzieren, Windows-Dateisystem-/Pfadtests, sichere Behandlung sehr großer Raster, GIS-Qualitätsprüfung, WebODM-Import und geometrische Modulflächenentzerrung. Keine automatische fachliche Freigabe.
- CI dieses Blocks noch nicht bestätigt. Bei Fehlern GitHub-Actions-Logs untersuchen und beheben; danach nächster Fünferblock mit nachvollziehbarer, offline persistierter GeoTIFF-Herkunft und Projektartefakt-Verknüpfung.

## Übergabe 15. Oktober 2026 – projektbezogene GeoTIFF-Herkunft in SQLite
- Branch `feature/block38-offline-ai-ingestion-tests`; vorheriger Stand bis `957c84d` in GitHub Actions grün. Keine Änderungen an `main` und keine PRs.
- Fünf Commits: `94ced22` (SQLite-Schema v17 und Migration v16→17), `9338268` (projektbezogene Speicher-/Abfrageoperationen), `e68df66` (Service registriert Pfad, Quelle, SHA-256 und beobachtete GIS-Metadaten), `f19b2f6` (Tests zu Persistenz, Projektisolation, Workflow-Unveränderlichkeit), dieser Dokumentationscommit.
- Neuer Datensatz `project_geotiffs` mit Projekt-Fremdschlüssel, kanonischem lokalem Dateipfad, `source_kind` (`webodm`, `external_gis`, `unknown`), SHA-256, CRS, Affintransform, Größe, NoData und ausschließlich `inspection_status='metadata_only'`. **Keine fachliche Genehmigung**, keine behauptete photogrammetrische Orthorektifizierung.
- Bestehende Datenbanken v16 werden migriert. Tests prüfen echten Offline-SQLite-Neustart und dass P2 keine Artefakte von P1 sieht.
- **Noch offen:** Desktop-Schaltfläche für explizite Registrierung (bisher nur Inspektion in GUI), Provenienzansicht, Abgleich gespeicherter Hashes bei erneutem Öffnen, atomare Datei-/Metadatenbindung, Lösch-/Umzugsfälle, große Dateien und Windows-Pfade. Es werden Referenzen auf externe Dateien gespeichert, keine Bilddateien kopiert.
- CI für diesen Block noch nicht bestätigt. Nach CI-Überprüfung Fehler korrigieren. Nächster Fünferblock: Registrierung mit ausdrücklicher Nutzeraktion in der Desktop-Importseite und persistierte Projekt-Artefaktliste anzeigen; niemals stillschweigend fachlich freigeben.

## CI-Nachbesserung – SQLite v17
- Der Fünferblock bis `86e4bb1` war **rot**: 6 Fehler bei 2868 bestandenen Tests (Python 3.11). Vier ältere Migrationstests erwarteten weiterhin Version 16, zwei synthetische Rückmigrationstests hatten `project_geotiffs` bereits angelegt.
- Korrekturcommits: `87f7783` (idempotentes `CREATE TABLE IF NOT EXISTS` in v16→17), `d746d3c`, `93bdba3`, `7abe67d` (Erwartung Schema v17 in den älteren Migrationstests), dieser Dokumentationscommit.
- **CI noch ausstehend**: neueste GitHub-Actions-Läufe prüfen. Falls weiterhin rot, Logs auswerten, keine neuen Features vor grünem Stand.
- Die v17-Migration bewahrt bestehende Tabellen und setzt nur das Schema-Flag fort. Keine fachliche GeoTIFF-Freigabe.

## CI-Nachbesserung 2 – letzte zwei Migrationstests
- CI-Lauf `38778810206` nach vorherigem Korrekturblock: 2872 bestanden, 2 fehlgeschlagen, 8 übersprungen. Nur noch `tests/test_sqlite_storage.py::test_schema_14_migration_does_not_invent_project_owners` und `::test_schema_15_migration_preserves_owner_without_inventing_capacity`; beide erwarteten Schema 16 statt 17.
- Commit `635bcccd` aktualisiert beide Versionsassertionen auf 17. Keine fachliche Logik verändert.
- Neueste GitHub Actions für diesen Commit prüfen, **noch nicht als grün bestätigt**. Bei Erfolg kann Desktop-GIS-Registrierung als nächster Fünferblock folgen.

## Übergabe 15. Oktober 2026 – Desktop-GeoTIFF-Registrierung
- Vorherige Korrekturcommits `635bcccd` und `ad148e7` laut GitHub Actions grün. Arbeitsbranch weiterhin `feature/block38-offline-ai-ingestion-tests`; kein Merge.
- Fünf Commits dieses Blocks: `a01a774` (Importseite: explizite Registrierung und persistierte Liste), `57992a3` (Desktop-Shell verbindet Service und SQLite), `f2457d8` (Button-Tests), `c55d7d9` (echte SQLite-Desktop-Neustart-/Projektisolationsprüfung), dieser Übergabecommit.
- Die GUI unterscheidet reine GeoTIFF-Metadatenprüfung von ausdrücklich gewählter dauerhafter Registrierung. Registrierung speichert vorerst `source_kind='unknown'`, weil WebODM-Herkunft nicht ohne Beleg behauptet werden darf. Einträge bleiben `metadata_only`; keine automatische Expertenfreigabe.
- Registrierte Einträge werden projektbezogen beim Öffnen geladen und mit Pfad, Herkunft, CRS und SHA-256 angezeigt. Der Test prüft Persistenz über Neustart, keine Fremdprojektanzeige und unveränderten Workflow.
- **Noch offen:** Herkunft im UI ausdrücklich erfassen (WebODM/externe GIS/unklar), Dateiverfügbarkeit und Hash-Abgleich bei erneutem Öffnen, Umgang mit Verschiebungen/Änderungen, doppelte Registrierung mit hilfreichem Hinweis, große Raster und Windows-Pfadtests, Sicherheitsgrenzen bei externen Dateireferenzen, fachliche GIS-Qualitätsprüfung.
- CI dieses Blocks noch nicht bestätigt. Bei roten Läufen zuerst Logs auswerten und Fehler beheben, keine neuen Features vor grünem Stand.

## CI-Nachbesserung – Desktop-GeoTIFF-Registrierung
- Die letzten beiden Commits des GUI-Fünferblocks (`c55d7d9`, `d072282`) waren rot; die ersten drei grün. CI-Lauf `38779772564`: 2876 bestanden, 1 fehlgeschlagen, 8 übersprungen.
- Ursache ausschließlich Textassertion im neuen Neustarttest: erwartete `nicht fachlich`, die GUI zeigt ausdrücklich `keine fachliche Freigabe`. Commit `654e2ae` passt den Test an die tatsächliche, fachlich richtige GUI-Aussage an. Keine Anwendungslogik geändert.
- **CI nach Fix noch nicht bestätigt.** GitHub Actions des letzten Commits prüfen, erst bei grünem Stand weitere Features entwickeln.

## Verbindliche Produktvorgabe – RGB- und Thermal-Orthofotos als GeoTIFF-Exporte (15.10.2026)
- **Ziel:** MCM-SolarCheck erzeugt aus den aufgenommenen RGB-Fotos ein RGB-Orthofoto und aus den Thermal-Fotos ein separates Thermal-Orthofoto. **Beide** werden als eigenständige, georeferenzierte GeoTIFF-Dateien gespeichert und dem Nutzer als **Exportdateien** angeboten.
- **Kein WebODM-Import als Soll-Prozess:** Die Orthofotos werden im Produkt aus den jeweiligen Aufnahmen erstellt. WebODM ist keine vorausgesetzte Datenquelle. Ein späteres GIS-Programm (z. B. QGIS) dient optional der **Weiterverarbeitung der exportierten Dateien**, nicht ihrer Bereitstellung an SolarCheck.
- GeoTIFF-Exporte erfordern echte, nachgewiesene Georeferenzierung (CRS/EPSG, affine Transformation, Auflösung, räumliche Ausdehnung, NoData wo sinnvoll). Vorschau-Stitching oder bloßes Umbenennen in .tif ist **kein** verifiziertes Orthofoto. Bei Thermal keine unbelegte Temperaturkalibrierung behaupten.
- **Stand vs. Ziel:** Die bisher implementierte GIS-Inspektion, manuelle Registrierung fremder GeoTIFF-Dateien und `source_kind='unknown'` sind Hilfs-/Zwischenfunktionen, **nicht** die Erfüllung dieser Vorgabe. Die eigentliche RGB-/Thermal-Orthofoto-Rekonstruktion und der Exportworkflow fehlen noch und sind vorrangig zu planen/implementieren. Frühere WebODM-bezogene Annahmen in Übergaben nicht als Soll-Architektur fortschreiben.
- Entwicklungsplanung entsprechend korrigieren: zunächst Architektur und verifizierbare Rekonstruktions-/Georeferenzierungsanforderungen für beide Modalitäten; danach echte Verarbeitung, GeoTIFF-Ausgabe, Projektpersistenz, Desktop-Export und End-to-End-Tests. Keine automatische fachliche Freigabe.

## Verbindliche Produktvorgabe – überlagerte RGB-/Thermal-Orthofotos im Desktop-Viewer (15.10.2026)
- Die **von MCM-SolarCheck selbst erzeugten** RGB- und Thermal-Orthofotos werden in einer gemeinsamen Desktop-Kartenansicht geografisch korrekt **übereinandergelegt** (WebODM-ähnlicher Ebenenvergleich, aber **kein WebODM-Import**).
- Ein **interaktiver Slider** erlaubt dem Nutzer, beide Ebenen überblendet anzusehen und zu untersuchen. Mindestens ein klar verständlicher RGB↔Thermal-Regler ist erforderlich; optional ergänzend eine verschiebbare Vergleichsgrenze.
- Beide Ebenen verwenden dieselbe räumliche Navigation (Zoom/Pan) und GIS-basierte Ausrichtung anhand der GeoTIFF-Georeferenzierung. Unterschiedliche Pixelauflösungen, CRS und Extents müssen kontrolliert behandelt werden; keine bloße pixelweise Überlagerung ohne geografische Registrierung.
- Anwender können dieselbe geografische Position bzw. dieselben PV-Module in beiden Ebenen untersuchen. RGB- und Thermal-GeoTIFFs bleiben **separat exportierbare Dateien**; der Slider verändert die Exportdaten nicht.
- **Stand vs. Ziel:** Ein solcher integrierter, GIS-korrekter Zwei-Ebenen-Viewer ist noch zu implementieren. Die bestehenden GeoTIFF-Inspektions- und Registrierungsfunktionen erfüllen diese Vorgabe nicht. Keine fachliche Freigabe oder unbelegte Thermal-Temperaturkalibrierung aus der Anzeige ableiten.
- Weitere Entwicklung: native RGB-/Thermal-Orthofoto-Erzeugung, korrekte gemeinsame Georeferenzierung, performante Rasteranzeige, synchroner Zoom/Pan, Slider, Untersuchung und Tests mit verschobenen Extents/verschiedenen Auflösungen als zusammenhängender Zielworkflow.

## Entwicklungsübergabe – GIS-basierte RGB-/Thermal-Ebenenvorschau (15.10.2026)
- Fünferblock: `0832dac` GIS-Ausrichtungsservice, `389c5ed` GIS-Ausrichtungstests, `bfb4c83` Qt-Ebenenvergleich mit Slider, `58de7da` Slider-Regressionstests, dieser Dokumentationscommit. Branch `feature/block38-offline-ai-ingestion-tests`, kein Merge.
- `services/orthophoto_layer_alignment.py`: liest zwei **bereits georeferenzierte** RGB-/Thermal-GeoTIFFs; projiziert Thermal-Werte mittels rasterio auf das RGB-Vorschauraster; NoData außerhalb der Abdeckung bleibt NaN; Vorschaugröße auf maximal 4096 begrenzt. Reprojektion ist nur eine **Anzeigeoperation**, keine Orthofoto-Erzeugung und kein GIS-Export.
- `gui/orthophoto_comparison.py`: `OrthophotoComparisonWidget` mit RGB/Thermal-Deckkraft-Slider 0–100; Thermal-Werte werden ausschließlich für die Bildschirmdarstellung relativ eingefärbt. **Keine Temperaturmessung oder Kalibrierung** aus der Farbskala ableiten. Quelldateien und Eingabearrays bleiben unverändert.
- Tests prüfen räumlichen Versatz, NoData, Vorschaugröße, getrennte Dateien, Slider und unveränderte Quelldaten.
- **Nicht fertig:** Widget ist noch **nicht in Shell/Workflow eingebunden**; kein gemeinsames Zoom/Pan, kein interaktives GIS-Koordinatenabfragen, keine echte RGB-/Thermal-Orthofoto-Rekonstruktion aus Einzelfotos, kein Thermal-GeoTIFF-Export. Es darf nicht als fertige Nutzerfunktion dargestellt werden.
- **Nächster Block:** Zunächst CI der fünf Commits prüfen. Danach kontrollierte Desktop-Anbindung des Vergleichs mit Projektkontext und Dateiauswahl, explizite Fehlerzustände/CRS- und Überlappungsprüfung; langfristig native orthorektifizierte Erzeugung beider GeoTIFFs und separate Exportaktion.

## Übergabe – Desktop-Anbindung RGB-/Thermal-Orthofoto-Slider (15.10.2026)
- Fünferblock auf `feature/block38-offline-ai-ingestion-tests`: `243ceff` Importseiten-Auswahl zweier GeoTIFFs; `cbc67bd` Shell-Anbindung der GIS-Ausrichtung und Anzeige; `d9f6afe` Button-/Abbruchtests; `b635582` Offline-Desktop-End-to-End-Test für Slider, Projektwechsel und Fehler; dieser Dokumentationscommit.
- Im geöffneten Projekt gibt es `compare_orthophotos_button`; zwei getrennte lokale GeoTIFFs werden per Dateidialog gewählt. `inspect_orthophoto_layer_pair` prüft beide Raster, `aligned_preview_arrays` richtet Thermal per GIS-Reprojektion auf die RGB-Vorschau aus. `OrthophotoComparisonWidget` zeigt den Deckkraft-Slider.
- Fehlende gemeinsame Rasterabdeckung wird ausdrücklich als Fehler angezeigt; Auswahlabbruch bewirkt keine Verarbeitung; bei Projektwechsel werden Vorschau und Fehlermeldung gelöscht. Viewer ist read-only, keine fachliche Freigabe, keine Temperaturkalibrierung.
- **Grenzen:** Noch keine automatische native RGB-/Thermal-Orthofoto-Rekonstruktion aus Drohnenbildern, keine GeoTIFF-Exportaktion, kein gemeinsames Zoom/Pan, keine gespeicherte Zuordnung eines Orthofoto-Paars. Die Auswahl existierender GeoTIFFs ist nur ein Zwischenschritt zur Viewer-Integration, nicht das endgültige Produktziel.
- CI für diesen Fünferblock noch nicht bestätigt. Bei Rot erst Testlogs prüfen und reparieren. Keine Änderungen an main oder PR ohne ausdrückliche Zustimmung.

## Übergabe – native planare Orthofoto-Erzeugung aus Originalfotos (15.10.2026)
- Fünferblock: `d96d374` Vermessungspunkt-basierte Homografie/Entzerrung; `0c0c544` RGB-/Thermal-Mosaik auf gemeinsamem GIS-Raster; `86b4325` getrennte RGB-/Thermal-GeoTIFF-Exporte; `2b1d259` Tests; dieser Dokumentationscommit.
- `orthophoto_planar_rectification.py` verarbeitet **Originalfotodateien**, nicht WebODM-TIFFs und nicht unverifizierte ORB-Previews. Voraussetzung sind pro Bild mindestens vier korrespondierende, tatsächlich vermessene Pixel-/Weltpunkte, ein ausdrücklich verifiziertes planares Flächenmodell und eine korrekte GeoTIFFSpatialReference. Residuen über zwei Ausgabepixel werden abgelehnt.
- `orthophoto_planar_mosaic.py` kombiniert entzerrte Aufnahmen zu einem vollständigen RGB- oder einkanaligen Thermal-Raster, mit Ressourcenlimit und Ablehnung nicht abgedeckter Extents. Einfache deterministische First-Coverage-Übernahme, noch **kein** Qualitäts-Blending/Seamline-Optimierung.
- `orthophoto_planar_export.py` schreibt separat `RGB GeoTIFF` und `Thermal GeoTIFF`, nie mit stillschweigendem Überschreiben. Thermal-Daten bleiben **unkalibrierte Rasterwerte**, ausdrücklich mit `MCM_THERMAL_CALIBRATION=unverified` markiert. QGIS ist nur optionaler nachgelagerter Verbraucher, nicht Input.
- **Einschränkung:** Dies ist ein **eng begrenzter, vermessungsbasierter planarer Rekonstruktionspfad**, kein allgemeines autonomes SfM/MVS-/DSM-Orthomosaik aus unkontrollierten M3T-Flugbildern. `controls_surveyed=True` und `planar_surface_verified=True` sind derzeit explizite Aufruferzusagen, keine automatische unabhängige Verifikation. Ohne vermessene Punkte ist keine GeoTIFF-Ausgabe erlaubt. Keine fachliche Freigabe.
- **Noch nicht umgesetzt:** Automatische Passpunktgewinnung/Photogrammetrie und 3D-Geländemodell, robuste unabhängige GCP-Validierung, radiometrische Thermal-Kalibrierung, Nutzeroberfläche für Passpunkte/Erzeugung/Export, automatisches Öffnen im RGB-/Thermal-Slider, Zoom/Pan, robuste Seamlines. Nicht als fertige Produktfunktion bezeichnen.
- **Nächster Block:** CI prüfen; dann zunächst Korrektheit/Qualität mit echten Bild- und vermessenen Referenzdaten validieren. Anschließend Benutzerworkflow für kontrollierte Orthofoto-Erzeugung und Verknüpfung mit dem Slider. Branch nicht nach main mergen ohne Freigabe.

## Übergabe – Qualitätssicherung planarer Orthofotos (15.10.2026)
- Fünf sequenzielle Commits: `27d2f50` erkennt kollineare Passpunkte und ungültige Homografien; `7eaaa1b` prüft Mosaik-Ressourcenlimit und nicht-endliche Thermal-Rasterwerte; `d892287` ergänzt Regressionstests; `082ba75` ergänzt einen separaten RGB-/Thermal-Rasterüberlappungsaudit; dieser Dokumentationscommit.
- Die neuen Prüfungen sind konservative technische Schutzmaßnahmen. Sie beweisen **nicht** unabhängig, dass vermessene Passpunkte oder das planare Flächenmodell fachlich korrekt sind. Der Audit meldet nur die nach GIS-Reprojektion endliche gemeinsame Rasterabdeckung; `georeferencing_verified=False` und `thermal_calibration_verified=False` bleiben ausdrücklich gesetzt.
- Noch offen: echte unabhängige GCP- und Residuenprüfung mit Messdaten, robuste Flugabdeckung, allgemeine SfM/MVS-/DSM-Orthofotoerzeugung, Thermal-Radiometrie, durchgängige Desktop-Bedienung, automatische Slider-Übergabe und Zoom/Pan.
- CI dieses Blocks ist noch nicht bestätigt; vor weiteren Features neue GitHub-Actions-Läufe prüfen und eventuelle Fehler beheben. Kein Merge auf main ohne Freigabe.

## Übergabe – synchroner RGB-/Thermal-Zoom im Windows-Viewer (15.10.2026)
- Fünferblock: `cbadd95` gemeinsame skalierbare Ansicht mit QScrollArea, Zoom +/- und 100%-Reset; `c28b6e8` Zoom-/Slider-Regressionstest; `a3a8706` explizite ganzzahlige Pixeldimensionen; `e5ec988` Zoom-Grenzen und Unveränderlichkeit der Quelldaten; dieser Dokumentationscommit.
- `OrthophotoComparisonWidget` stellt die **bereits GIS-ausgerichteten** RGB-/Thermal-Pixel in einem einzigen gemeinsamen Bild dar. Der Slider ändert nur die Darstellung. Zoom 25–400 % und Verschieben mittels Scrollbars gelten für beide Ebenen zugleich. Das ist bildbasierte Navigation auf dem gemeinsamen Vorschau-Raster, noch keine vollwertige GIS-Kartenansicht mit Koordinatenanzeige.
- Unverändert: zwei getrennte GeoTIFF-Dateien, keine Überschreibung, keine Temperaturkalibrierung, keine fachliche Freigabe. Noch ausstehend: verifizierte allgemeine Orthofotoerzeugung aus M3T-Flugaufnahmen, durchgängige Desktop-Erzeugung und Export, automatisches Laden eigener Ergebnisse, Qualitätskontrolle mit vermessenen Daten.
- CI für diesen Block erst nach den GitHub-Actions-Läufen bestätigen. Keine Änderung an main ohne ausdrückliche Freigabe.

## Übergabe – Winkelabhängigkeit Kamera und PV-Modulebene (15.10.2026)
- Fünferblock: `862bf80` führt Kamera-/Modulebenen-Metadaten und konservative Diagnostik ein; `9e3a592` trennt Metadatenvollständigkeit von tatsächlicher Rekonstruktionsfreigabe; `d65430d` prüft ungültige DJI-Posen und fehlende unabhängige Modulwinkel; `1ab349e` aktualisiert die verbindliche Modulflächenrichtlinie; dieser Dokumentationscommit.
- Fachvorgabe: DJI GimbalPitch/Roll/Yaw beschreiben die Kamerapose, **nicht** den Einfallswinkel zur geneigten PV-Fläche. Modulneigung und Azimut sind separat vermessen oder rekonstruiert mit Herkunft und Konfidenz. Mehrere Dachflächen getrennt behandeln. Horizontaler Orthofoto-Überblick und entzerrte Modulebenenansicht sind zu unterscheiden.
- Der neue Readiness-Service ist ein isolierter konservativer Baustein; noch **keine** Verdrahtung mit den bestehenden Importer-Pose-Feldern, kein Kameramodell, keine Projektion eines Strahls auf eine 3D-Ebene, keine automatische Winkelkorrektur und keine fachlich geprüfte Rekonstruktion. `ready_for_reconstruction` ist bewusst stets `False` bis diese unabhängigen Gates implementiert sind.
- Als Nächstes: bestehende Importer-Pose-Datenstruktur prüfen und ohne erneutes JPEG-Parsing anbinden; explizite Koordinatensysteme/Kameraextrinsik, intrinsische Kalibrierung und unabhängige Passpunkte nachweisen; synthetische schräge Modulflächen und reale GCP-Datensätze testen; anschließend Desktop-Erzeugung und Slider-Übergabe. CI noch zu prüfen. Kein Merge nach main ohne Freigabe.

## Übergabe – DJI-Importer-Pose an Modulflächengeometrie angebunden (15.10.2026)
- Fünf Commits: `15fa3c7` Adapter `domain.models.Pose` zu `CameraOrientation` ohne erneutes XMP-/JPEG-Parsing; `af87bfe` Achsen- und Modulneigungstests; `3c55fde` Batchdiagnostik für bereits importierte Frame-Objekte mit `camera_pose`; `079752d` Batchtests mit fehlenden Kamerawinkeln; dieser Dokumentationscommit.
- DJI `GimbalPitchDegree`, `GimbalRollDegree`, `GimbalYawDegree` werden bereits in `importers/m3t_xmp.py` als `camera_pose: Pose` übernommen und in `ThermalFrame.camera_pose` transportiert. Der neue Adapter verwendet genau dieses Modell. Die unabhängige Modulneigung und der Azimut dürfen daraus nicht abgeleitet werden.
- Der Adapter ist ein geprüfter Servicebaustein, aber noch nicht in die Desktop-Projektseite verdrahtet; er führt keine photogrammetrische Winkelkorrektur aus. `metadata_complete=True` ist ausdrücklich keine Rekonstruktionsfreigabe; `ready_for_reconstruction=False` bis intrinsische Kamerakalibrierung, Extrinsik/Koordinatenkonvention, Passpunktkontrolle und Modulflächenrekonstruktion belastbar implementiert sind.
- Nächste Schritte: reale importierte Frame-Persistenz/Projekt-Service-Anbindung, Kamerakalibrierung, explizite Welt-/Kamerakoordinatensysteme, geneigte Ebenen mit gemessenen Referenzpunkten, GIS-Ausgabe und Windows-Workflow. CI für diese fünf Commits noch nicht bestätigt; kein Merge nach main ohne ausdrückliche Freigabe.

## Übergabe – kalibrierte Kamerastrahlen auf geneigte PV-Modulebene (17.10.2026)
- Fünferblock: `e5f8e1f` implementiert die reine 3D-Strahl/Ebenen-Schnittberechnung; `90a054c` fügt synthetische Tests für horizontale und geneigte Ebenen sowie Fehlerfälle hinzu; `298cf55` korrigiert die erwartete Richtung der perspektivischen Verkürzung im Test; `104d388` dokumentiert ENU-/Kamerakoordinaten und Sicherheitsgrenzen; dieser fünfte Commit aktualisiert die dauerhafte Übergabe.
- Schnittstelle `services/module_plane_projection.py`: kalibrierte Pinhole-Intrinsik, explizite Kamera-zu-ENU-Rotation und Kamerazentrum, unabhängig vermessene 3D-Modulebene. Kamera x rechts, y unten, z vorwärts; ENU Ost/Nord/Oben; Pixel müssen bereits entzerrt sein. Nichtfinite Daten, nichtorthonormale Rotationen, parallele und rückwärts gerichtete Strahlen werden abgelehnt.
- **Keine unzulässige Abkürzung:** DJI-Gimbalwinkel dürfen nicht ohne geprüfte Achsenkonvention und Kalibrierung in diese Rotation umgerechnet werden. Der neue Dienst erzeugt 3D-Schnittpunkte, **noch keine** Orthofotos oder GeoTIFFs und keine Qualitätsfreigabe. Synthetische Tests sind kein vermessener Genauigkeitsnachweis. RGB-/Thermal-Georeferenzierung und Desktop-Slider bleiben separate Integrationsaufgaben.
- Nächster Block: nach CI explizite DJI-Achsen-/Kamera-Konvention und kalibrierte Intrinsik aus verifizierter Quelle integrieren; unabhängige 3D-GCPs/Modulflächen und Reprojektionsfehler prüfen; dann echte winkelabhängige Entzerrung und GeoTIFF-Workflow in der Windows-GUI. Kein Merge nach main ohne ausdrückliche Freigabe. CI-Status bei Übergabe noch offen.

## Übergabe – metrische Koordinaten auf geneigter PV-Modulebene (17.10.2026)
- Fünferblock: `1930c8f` ergänzt eine deterministische lokale ENU-Modulebenenbasis, `ffa67fa` prüft horizontale/geneigte Abstände und abweichende Punkte, `7c9fabd` verbindet die kalibrierte Strahl-Ebenen-Schnittberechnung mit lokalen Oberflächenkoordinaten, `0713287` ergänzt einen synthetischen Ende-zu-Ende-Geometrietest; dieser fünfte Commit dokumentiert die Übergabe.
- `services/module_plane_basis.py` verwendet den unabhängig festgelegten ENU-Ebenenpunkt als Ursprung, projiziert Ost (bei Singularität Nord) als lokale u-Achse in die Ebene und bildet v als Normalen-Kreuzprodukt. So sind Oberflächenabstände metrisch, ohne Dachneigung aus DJI-Pitch abzuleiten. Die Schnittstelle `project_image_pixels_to_plane_coordinates` nimmt bereits entzerrte Pixel, kalibrierte Pinhole-Intrinsik, unabhängig verifizierte Kameraextrinsik und vermessene 3D-Ebene entgegen.
- Grenzen: keine automatisierte DJI-Orientierungskonvertierung, keine Linsenverzeichnungskorrektur, keine geprüften Kamerakalibrierdaten, keine GIS-CRS-Transformation, kein Rasterwarping, keine automatische RGB-/Thermal-Orthofoto-Erstellung und keine Qualitätsfreigabe. Die neuen Tests verwenden ausschließlich synthetische Geometrie; reale vermessene GCPs fehlen.
- Nächste Schritte: nach grüner CI die explizite Kalibrierung und Posekonventionen mit verifizierten DJI-M3T-Daten sichern; metrische Ebenenkoordinaten und GIS-Koordinaten anhand unabhängiger Passpunkte verknüpfen; erst dann kontrollierte Entzerrung, getrennte GeoTIFF-Exporte und Desktop-Slider-Integration. Kein Merge nach main ohne Freigabe. CI-Status dieses Blocks noch offen.

## Übergabe – Kontrollpunktprüfung geneigter Modulflächen (17.10.2026)
- Commits: 3cb165c (metrischer Kontrollpunktvergleich), b04add1 (synthetische Tests), fcde032 (Eingabevalidierung), fd342e5 (weitere Regressionstests), dieser Dokumentationscommit.
- Neuer Dienst: module_plane_control_audit.py. Vergleicht kalibrierte Kamerastrahlen mit unabhängig angegebenen 3D-Passpunkten. Prüft mindestens vier unterschiedliche, nicht kollineare Kontrollen, Ebenenabstand, RMS und Maximalfehler in Metern. Keine automatische Freigabe: independently_verified bleibt False.
- Noch offen: echte vermessene Prüfpunkte, geprüfte DJI-Kalibrierung und Posekonvention, unabhängige Qualitätsprüfung, Bildentzerrung, GeoTIFF-Exporte und Windows-GUI-Integration. Synthetische Tests belegen keine Feldgenauigkeit. CI offen. Kein Merge nach main ohne Freigabe.

## Übergabe – explizites Kalibrierungstor für importierte DJI-Aufnahmen (17.10.2026)
- Fünferblock: 032d0e3 führt das Kalibrierungstor ein; e8d9913 ergänzt Sicherheits- und Positivtests; 0ef7b39 verweigert boolesche Winkel und Brennweiten; 838936c ergänzt Tests für ungültige Rotationen; dieser Commit aktualisiert die Übergabe.
- `services/module_camera_calibration_gate.py` nimmt bereits importierte `ImageFrame.camera_pose` und separat bereitgestellte `VerifiedCameraGeometry` entgegen. Verlangt endliche vollständige DJI-Pose, kalibrierte Pinhole-Intrinsik, passende Bildgröße, echte Kamera-zu-ENU-Rotation, explizite Herkunft von Kalibrierung, Rotation und Vermessung sowie bestätigte Linsenentzerrung und Referenzrahmen. Kein erneutes Lesen von JPEG/XMP und keine automatische Interpretation von Gimbalwinkeln.
- Sicherheitsgrenze: die booleschen Prüffelder und Herkunftstexte sind Angaben des Aufrufers, kein unabhängiger Zertifizierungsnachweis. Ohne verifizierte DJI-Konvention, Kamera- und Linsenkalibrierung sowie vermessene 3D-Kontrollpunkte keine fachliche Geometriefreigabe. Noch keine automatische Bildentzerrung, native RGB-/Thermal-Orthofotos oder GUI-Verbindung. Synthetische Tests sind keine Feldvalidierung.
- Nächster Schritt: echte kalibrierte M3T-Kamera- und Posequellen einschließlich Referenzrahmen dokumentieren, unabhängige GCP-Prüfung mit diesen Daten durchführen und anschließend die Modulebenen-Entzerrung in den Offline-Desktop-Workflow integrieren. CI offen; kein Merge nach main ohne Freigabe.

## Übergabe – metrische Bildentzerrung geneigter Modulflächen (17.10.2026)
- Fünferblock: e47d5f4 implementiert inverses Raster-Sampling einer geneigten 3D-Modulebene; dbf2142 prüft RGB- und Thermal-Rohwerte synthetisch; cc70634 schützt Remap-Koordinaten; 24bf6ca erweitert Fehlerfalltests; dieser Dokumentationscommit aktualisiert die Übergabe.
- `services/module_plane_rectification.py`: `rectify_module_surface` verwendet bestehende `ImageFrame.camera_pose`, ausdrücklich bereitgestellte `VerifiedCameraGeometry`, eine unabhängig vermessene ENU-Modulebene und ein begrenztes metrisches Oberflächenraster. Rückprojektion der Rasterpixelzentren über Kameraextrinsik und kalibrierte Pinhole-Intrinsik, `cv2.remap`, gültige Pixelmaske. RGB und unkalibrierte Thermal-Rohwerte sind möglich; keine Celsius-Zuschreibung. Kein erneutes DJI-XMP-Parsen.
- Sicherheitsgrenzen: Eingangsbild muss bereits linsenentzerrt sein, die entsprechenden Flags und Herkunftstexte sind nur Angaben des Aufrufers. Keine verifizierte DJI-Rotationskonvention, keine unabhängig nachgewiesene Vermessungsgenauigkeit, kein echtes GIS-CRS, keine GeoTIFF-Ausgabe, kein automatisches Fotomosaik und keine Windows-GUI-Anbindung. Ausgaben tragen `georeferencing_verified=False` und `thermal_calibration_verified=False`. Synthetische Tests ersetzen keine echten M3T-Feldtests.
- Nächster Block: reale Kamera-/Passpunktkalibrierung und kontrollierte Oberflächen-Rasterausdehnung, anschließend GIS-Referenzierung, getrennte native RGB-/Thermal-GeoTIFFs und Desktop-Slider. CI noch offen; kein Merge nach main ohne Freigabe.

## Übergabe – gemeinsames metrisches Modulflächenmosaik (17.10.2026)
- Fünferblock: 26c066e implementiert die Zusammenführung bereits entzerrter Aufnahmen auf einem identischen metrischen Modulflächenraster; 609a64c ergänzt synthetische Tests für Abdeckung und Überlappung; c0a8af9 prüft Rastergeometrie vor der Speicherallokation; 0c63ca3 ergänzt Sicherheits- und Dimensionsprüfungen; dieser fünfte Commit hält die Übergabe fest.
- `services/module_surface_mosaic.py`: deterministische Priorität des ersten gültigen Bildpixels, gültige Pixelmaske, Abdeckungsquote, Anzahl beitragender Bilder je Rasterzelle; optionale strenge Vollabdeckung, Pixelbudget, Rastertyp- und Rastergleichheitsprüfung. Thermal-Rohwerte werden nicht gemittelt oder als Celsius deklariert. Eingaben mit unzulässigen Verifikationsbehauptungen werden zurückgewiesen.
- Noch offen: kontrollierte automatische Festlegung der Rasterausdehnung, belastbare DJI-Kamerakalibrierung und Referenzrahmen, unabhängige Feld-GCP-Prüfung, echte GIS-CRS-Anbindung, native RGB-/Thermal-GeoTIFF-Generierung aus importierten Fotos sowie Windows-GUI-Integration. Mosaik ist nur lokal metrisch und nicht georeferenziert. CI dieses Blocks noch offen; kein Merge nach main ohne ausdrückliche Freigabe.

## Übergabe – kontrollierte Rasterausdehnung geneigter PV-Modulflächen (17.10.2026)
- Fünferblock: dd2cd53 ergänzt den metrischen Rasterplaner aus vermessenen ENU-Eckpunkten; 12a4b65 prüft waagerechte und geneigte Module synthetisch; bcc47af verwirft nahezu kollineare Eckpunkte; a958ed9 ergänzt Fehlerfalltests; dieser fünfte Commit dokumentiert die Übergabe.
- `services/module_surface_grid_planning.py`: `plan_surveyed_module_grid` projiziert unabhängig vermessene 3D-Modul-Eckpunkte in die lokale orthonormale Modulebene, bestimmt ihre metrischen Grenzen und berechnet ein Raster mit expliziter Auflösung und Pixelbudget. Die geneigte Oberflächenlänge wird nicht durch horizontale Projektion ersetzt. Degenerierte, nichtfinite und von der Ebene abweichende Kontrollpunkte werden zurückgewiesen.
- Das Ergebnis ist ein lokales metrisches `ModuleSurfaceGrid`, keine GIS-CRS-Transformation und keine verifizierte GeoTIFF-Georeferenzierung. Noch keine eigenständige Vermessung der Eckpunkte, keine geprüfte DJI-Kalibrierung, keine automatische Fotomosaik-GUI oder native RGB-/Thermal-GeoTIFF-Erzeugung aus importierten Aufnahmen. Keine thermische Temperaturkalibrierung wird behauptet.
- Nächste Schritte: unabhängig geprüfte Feldkontrollen und ENU-zu-GIS-Verankerung; Rasterplaner, Entzerrung und Mosaik im Projekt-Workflow verbinden; anschließend echte georeferenzierte RGB-/Thermal-Exporte und synchronisierte Windows-Vergleichsansicht. CI noch offen; kein Merge nach main ohne Freigabe.

## Übergabe – durchgängige metrische Modulflächen-Verarbeitung (17.10.2026)
- Fünferblock: 2a05fdd verbindet vermessene Rasterplanung, kalibrierte Bildentzerrung und Modulflächenmosaik; 7816a17 ergänzt synthetische Integrationstests; 340204c verlangt eindeutige importierte Frame-IDs; 69a99cf prüft Identitätsfehler; dieser fünfte Commit dokumentiert den Stand.
- `services/module_surface_pipeline.py`: `build_metric_module_surface` verarbeitet bereits importierte `ImageFrame`-Objekte, separat geprüfte Kamerageometrien und bereits linsenentzerrte RGB-/Thermal-Raster mit unabhängig vermessenen ENU-Modul-Eckpunkten. Ergebnis: lokales metrisches Mosaik mit Pixelmaske, Abdeckungsquote und Beitragszählung. Kein erneutes JPEG/XMP-Parsen, keine DJI-Pitch-zu-Dachneigung-Konvertierung.
- Sicherheit: positive metrische Auflösung, Pixelbudget, eindeutige Frame-IDs, bestehende Kalibrierungstore und optional strikte Vollabdeckung. RGB und Thermal werden nicht stillschweigend radiometrisch gemischt; Thermal-Rohwerte sind keine Celsius-Werte. Synthetische Tests ersetzen keine Feldvalidierung.
- Noch nicht erreicht: echte überprüfte DJI-Kalibrierung, automatische Kamerapose-/Linsenentzerrungsgewinnung, unabhängige Vermessungsdaten, GIS-Verankerung, echte getrennte GeoTIFF-Orthofotos aus importierten Bildern und Windows-GUI-Verkabelung. Nächste Schritte: reale M3T-Kalibrierdaten, unabhängig geprüfte ENU-zu-CRS-Transformation und native Exportintegration. CI offen; kein Merge nach main ohne Freigabe.

## Übergabe – vermessene GIS-Kontrollpunktprüfung für Modulflächen (17.10.2026)
- Fünferblock: 14da6f2 ergänzt diagnostischen lokalen Modulflächen-zu-GIS-Affine-Fit; a6762e0 prüft synthetische Kontrollpunkte; ad09e00 schützt gegen schlecht konditionierte Transformationen; 286dc45 ergänzt Regressionstests; dieser fünfte Commit dokumentiert die Übergabe.
- `services/module_surface_gis_control.py`: `audit_surface_gis_controls(surface_uv_m, surveyed_crs_xy_m, tolerance_m=...)` erwartet mindestens vier unabhängige, zweidimensional verteilte, endliche Kontrollpunktpaare, berechnet eine affine Näherung und meldet RMS-/Maximalfehler und Toleranzstatus. `independently_verified` bleibt ausdrücklich `False`. Die CRS-Kennung und die unabhängige Vermessung werden NICHT aus DJI-Metadaten abgeleitet.
- Noch keine Exportfreigabe: Ein numerisch guter Affine-Fit beweist weder unabhängige Vermessung noch CRS-Richtigkeit, insbesondere bei geneigten Modulflächen. Der metrische Modulflächenraster ist eine separate entzerrte Ansicht; die kartografische Draufsicht kann zusätzliche Orthorektifikation benötigen. Keine automatische GeoTIFF-Erzeugung, keine Temperaturkalibrierung und keine Windows-GUI-Verkabelung durch diesen Block.
- Nächster Schritt: explizites, extern verifiziertes CRS- und Kontrollpunkt-Provenienzmodell, unabhängige Kontrollpunkte (nicht nur Fitpunkte), und geprüfte GIS-Exportintegration für getrennte RGB-/Thermal-Geotiffs. CI offen, kein Merge nach main ohne ausdrückliche Freigabe.

## Übergabe – Priorität native Orthofotos und Prüfbericht (17.10.2026)
- Nutzerpriorität ausdrücklich geändert: weitere eigenständige GIS-Forschung zurückstellen. Fokus auf native Erzeugung getrennter RGB-/Thermal-Orthofotos aus importierten Drohnenfotos und vollständigen fachlich geprüften Kundenbericht. GIS-CRS bleibt nur als notwendige technische Exportvoraussetzung bestehen.
- Fünferblock: f1d1395 erzeugt aus bereits vorhandenem RGB-GeoTIFF eine lokale, begrenzte PNG-Berichtsabbildung ohne Veränderung der Quelle; 6c88f62 testet Rasterfarben, Dimensionen und Dateischutz; d198920 trennt im Bericht sichtbares Orthofoto vom nicht nachgewiesenen Flugpfad; 4767baf testet die tatsächliche PDF-Einbettung; dieser fünfte Commit dokumentiert die Übergabe.
- `services/orthophoto_report_overview.py`: bestehende echte 3-Band-uint8-RGB-GeoTIFFs mit CRS und expliziter RGB-Bandsemantik werden für den Bericht sicher verkleinert. Keine ungesicherte Flugpfadbehauptung, keine falsche Celsius-Kalibrierung, kein Überschreiben bestehender Dateien. PDF nutzt bestehenden `export_pilot_pdf`-Pfad und bestehende Berichtsvorlage.
- Das ist ein Berichts-Integrationsbaustein, noch KEINE native automatische Orthofoto-Erzeugung aus DJI-Bildern. Der bisherige native planar-vermessene Orthofoto-Workflow ist eng begrenzt; die allgemeine photogrammetrische RGB-/Thermal-Erzeugung und die GUI-Anbindung sind offen.
- Nächster Block: echte importierte RGB-/Thermalaufnahmen mit bestehendem Orthofoto-Workflow verbinden, verifizierte Orthofoto-Ergebnisse im Projekt registrieren und im bestehenden Prüfbericht einschließlich Bildnachweisen darstellen; keine unkontrollierte KI-Freigabe. CI dieses Blocks offen; kein Merge nach main ohne Freigabe.

## Übergabe – Orthofoto-Abbildung direkt im PDF-Berichtsablauf (17.10.2026)
- Priorität bleibt native Orthofoto-Erzeugung und fachlich geprüfter Kundenbericht, keine zusätzlichen eigenständigen GIS-Themen.
- Fünf Commits: 48e7d81 ergänzt `export_pilot_pdf_with_rgb_orthophoto` als lokale Orchestrierung vorhandener RGB-GeoTIFFs zum bestehenden Pilot-PDF; 0067acd testet PDF und Bereinigung temporärer Vorschauen; 0912a7e prüft den bestehenden `PilotReport`-Vertrag vor der Verarbeitung; 0679cee testet Ablehnung ungültiger Berichte und Überschreibschutz; dieser fünfte Commit ist die Übergabe.
- Der Ablauf nutzt `create_rgb_orthophoto_report_preview`, `export_pilot_pdf` und eine temporäre Vorschau im Zielverzeichnis. Er erzeugt keine zusätzlichen permanenten Bilddateien, behauptet keinen Flugpfad und ändert das Original-GeoTIFF nicht. PDF-Befunde bleiben durch den bestehenden Report-Vertrag auf geprüfte Inhalte begrenzt.
- Noch nicht implementiert: allgemeine native RGB-/Thermal-Orthofoto-Erzeugung aus echten DJI-Bildfolgen, automatische Kopplung an den Projektimport, interaktiver Windows-Workflow. Der enge surveyed-planar Generator bleibt bisher die einzige echte native GeoTIFF-Erzeugung aus Originalbildern. Nächster Fünferblock sollte gezielt diese Erzeugung/Import-Verknüpfung angehen, nicht weitere bloße Berichtsvorschauen.
- CI für diesen Block noch nicht bestätigt; kein Merge nach main ohne Nutzerfreigabe.
