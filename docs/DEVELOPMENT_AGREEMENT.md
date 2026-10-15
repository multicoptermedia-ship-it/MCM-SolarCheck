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
