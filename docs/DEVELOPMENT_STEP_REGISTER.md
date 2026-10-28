# Verbindliches Entwicklungsregister – MCM-SolarCheck

> **Aktuelles Gate und einzige Folgeaufgabe:** [AKTUELLER_ENTWICKLUNGSSTAND.md](AKTUELLER_ENTWICKLUNGSSTAND.md). Die nachfolgende Chronik ist ein Belegregister, kein Plan zur Wiederholung historischer nächster Schritte.

**Gilt ab:** 26.10.2026. **Autoritative Git-Quelle für abgeschlossene Arbeiten:** `main` **nach dem CI-geprüften Fast-forward vom 26.10.2026**. Bisherige Arbeiten sind im Quellzweig `feature/offline-human-report-approval` historisch enthalten. Neue Entwicklung in kleinen Featurebranches und erst nach Gate in `main`. **Nicht ersetzen**: Sicherheits-/Freigaberegeln in [DEVELOPMENT_AGREEMENT.md](DEVELOPMENT_AGREEMENT.md).

## Unverhandelbarer Ablauf ab jetzt

1. **Vor der Implementierung:** [PROJECT_START_HERE.md](PROJECT_START_HERE.md), [REPOSITORY_BRANCH_INVENTORY_2026-10-26.md](REPOSITORY_BRANCH_INVENTORY_2026-10-26.md), dieses Register, Entwicklungsvereinbarung, Chat-Übergabe und aktuelle Fachroadmap lesen. Bestehende Funktionen und bereits belegte Nutzerresultate feststellen; keine unnötigen Wiederholungstests oder isolierten Endlosschleifen.
2. **Immer ein kleiner vertikaler Schritt:** konkreter Benutzerweg (Projekt → echte Eingabe → nachvollziehbarer Verarbeitungsschritt → sichtbares Ergebnis/Fehlerstatus), vollständig offline auf Windows 10 ausgelegt. Technische Unterfunktionen nur einbauen, wenn sie diesem Benutzerweg dienen. Keine irreführende Qualitäts-/Vermessungsfreigabe.
3. **Für jeden abgeschlossenen Code- oder Entwicklungsblock:** Noch im **selben Branch** diesen Eintrag ergänzen: Datum, ID, Ziel, geänderte Dateien, SHA, Vorbedingungen, reale/synthetische Belege, CI-Links inkl. Windows-3.11/3.12, Sicherheits-/Qualitätsgrenzen, Abnahmestatus auf Nutzerhardware, offene Restarbeit und exakte nächste Aktion.
4. **Dokumentation muss mit dem Code synchron sein:** im selben Abschlussblock ebenfalls `docs/DEVELOPMENT_AGREEMENT.md`, `docs/CHAT_HANDOFF.md` und bei PV-Arbeit `docs/PV_ORTHOMOSAIC_FIRST_ROADMAP.md` mit kurzem Verweis auf den Registereintrag aktualisieren. Die 5-Commit-Übergabe ist eine bewährte Regel, aber wichtiger ist: **keine undokumentierte abgeschlossene Funktion**.
5. **Nach dem Dokumentationscommit:** HEAD und neue CI-Runs nachprüfen. Kein grünes Ergebnis für neue Commits aus älteren erfolgreichen Runs ableiten. `main`, Release-/Experiment-/PR-Branches nicht ohne separaten schriftlichen Integrationsauftrag ändern.
6. **Evidenz strikt unterscheiden:** GitHub-Synthetiktests ≠ echte Windows-10-Nutzerabnahme; MPO-/GPS-Metadaten ≠ validierte Kamerapose; ORB/optische Vorschau ≠ vermessenes Orthofoto; M3T-raw16 ≠ °C; Vorschlag ≠ bestätigtes Modul/Befund; automatischer Bericht ≠ Fachfreigabe.
7. **Neuer Chat:** zuerst das [PROJECT_START_HERE.md](PROJECT_START_HERE.md) lesen und den letzten Registereintrag als Ausgangspunkt benutzen; bereits dokumentierte Belege nicht erneut vom Benutzer einfordern. Bei fehlendem Zugriff auf GitHub offen benennen, statt alte Ergebnisse zu erfinden.

## Format des nächsten Eintrags

```markdown
### YYYY-MM-DD · DEV-XXXX – Kurzname
- Branch / Start-HEAD / Abschluss-HEAD:
- Nutzerziel und vertikaler Arbeitsweg:
- Neue/geänderte Dateien, bereits wiederverwendete Module:
- Validierung: synthetische Tests; echte Nutzerdaten; Windows-Betrieb (getrennt!):
- CI: tests und windows-offline-validation, Python 3.11/3.12, konkrete Action-Links:
- Einordnung: implementiert / geprüft / lokal abgenommen / freigegeben:
- Grenzen und fail-closed-Gates:
- Nutzer-/Datenschutz (Originale, Test-SQLite, Produktions-SQLite):
- Dokumentations-Updates:
- Offene Fragen und nächster einziger vertikaler Schritt:
```

## Historischer Index (nicht neu ausführen)

| Stand | Dokumentierte abgeschlossene Erkenntnis | Einstufung |
|---|---|---|
| Vor Oktober 2026 | DJI-M3T-Importer, APP3-Rohdatenpfad, RGB-/Thermal-Pairing, Modul/Cadence-Ansätze, SQLite-/Review- und Exportgates | Über Vorgängerbranches im aktuellen Branch historisch enthalten; einzelne Fachbelege in bisherigen Dokumenten |
| 21.10.2026 | RGB-Flugbildregistrierung, Ketten und Segmentvorschau | `feature/rgb-all-segments-export` historisch im aktiven Branch enthalten; nichtmetrisch |
| 25./26.10.2026, A–E | Geneigte Oberflächen, RGB-Kachelplanung, kachelweise RGB-Entzerrung, Mehrbildkacheln, abrechbarer RGB-Dachflächenpilot | `6f25e00` synthetisch + GitHub-CI grün; **keine** reale Dachsurvey-/Orthofoto-Abnahme |
| 26.10.2026, vertikaler Erstweg | `rgb_project_preview_vertical.py`, `rgb_project_preview_cli.py`, `tests/test_rgb_project_preview_vertical.py`: importiertes Projekt → originale RGB-Bilder → diagnostisches PNG/JSON | `0a29e6a` Python + Windows CI grün; auf alter lokaler Windows-App **noch nicht installiert/getestet** |
| 26.10.2026, Inventur | Alle 14 vorhandenen Branch-HEADs, vollständige Bäume, Vergleiche, GitHub-Actions-HEAD-Status, Datenschutz-Experiment und PRs katalogisiert | [Branch-Katalog](REPOSITORY_BRANCH_INVENTORY_2026-10-26.md); Repository-Dokumentation statt redundanter PowerShell-Prüfungen |

## Aktueller Übergabestatus

**Nächster sinnvoller vertikaler Schritt nach dieser Bestandserhebung:** gezielte GUI-Anbindung für den bereits vorhandenen Projekt→2-RGB-Originale→PNG/JSON-Preview-Weg, mit echtem Nutzerstatus und Abbruch; erst nach UI-/Eingabeprüfung und eigenständiger Kalibrierung eine tatsächlich maßhaltige Dachflächen-RGB-Ausgabe. Keine Neuerfindung der bereits vorhandenen Importer/MPO-Diagnostik/Feature-Matcher.

**Fachliche Dauergrenzen:** geneigte Dachflächen und 20–30° Freiflächenaufständerung stets gegen reale Oberflächennormalen geometrisch behandeln; Nadirkamera ist nicht automatisch senkrecht zur Modulfläche; keine vermessungsfremden Koordinaten erfinden; Offline/Privatheit/Fachfreigabe bleiben verbindlich.

**Inventur-Commit und CI:** Werden nach der Aktualisierung des Registers separat überprüft und im nächstfolgenden Registereintrag nachgetragen; keinesfalls vorab als grün behaupten.

### 2026-10-26 · DEV-INV-001 – Vollständige 14-Branch-Bestandsaufnahme
- **Branch / Start-HEAD:** `feature/offline-human-report-approval`, vor der Inventur `0a29e6a66d2ca0b23962f50b09ce099a2decaf5a`.
- **Inventur-Dokumentationscommit:** `6ac92bfdf9bada682e89c730d07646e1379d66ad`. Danach folgte eine rein dokumentarische Korrektur/README-Wegweiser-Aktualisierung; der tatsächliche End-HEAD ist stets über GitHub zu prüfen.
- **Benutzerziel:** Kein erneutes Erfinden bereits entwickelter Funktionen; sämtliche 14 Branches als gegliederte, nachvollziehbare Git-Wissensbasis und als PDF-Bericht sichern.
- **Neue/aktualisierte Dateien:** `docs/REPOSITORY_BRANCH_INVENTORY_2026-10-26.md`, `docs/DEVELOPMENT_STEP_REGISTER.md`, `docs/PROJECT_START_HERE.md`, README-Einstiegsverweis, Kurzverweise in `docs/DEVELOPMENT_AGREEMENT.md`, `docs/CHAT_HANDOFF.md`, `docs/PV_ORTHOMOSAIC_FIRST_ROADMAP.md`.
- **Validierung:** Für jeden Branch Git-HEAD, Datums-/Titel-Commit, vollständiger File-Tree ohne Trunkierung, Historienrelation zum aktiven Branch und GitHub-Actions-HEAD (wenn vorhanden). Zwei offene PRs nicht verändert. PDF aus demselben datierten Bestandsdatenstand erzeugt; visuelle Renderkontrolle.
- **CI dieses ersten Inventur-Commits:** `6ac92bf`: [tests (3.11/3.12)](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40361333242) **success**; [Windows (3.11/3.12)](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40361333253) **success**.
- **Status:** Branch-Wissensinventur und Verfahrensregeln dokumentiert; **keine neuen Laufzeitfunktionen, kein Merge, keine Nutzerdaten geändert**. PDF datierter Snapshot, Git-Markdown dauerhaft pflegen. Der spätere README-/Korrekturcommit benötigt eigene finale CI-Prüfung.
- **Risiken/Grenzen:** `main`/ `images` identisch und nicht lauffähiger Quellstand; drei Zwei-Agenten-Branches divergent, QA-HEAD rot (privater Exportpfad in GUI-Fehlermeldung), Integration-Review grün. Keine pauschale Funktionsgleichheit der divergierten Experimente ableiten.
- **Nächste Benutzeraktion:** Keine Wiederholung von MPO/EXIF/ORB-Lesetests; nach Sichtung dieses Berichts gezielt vertikalen RGB-Projekt→Preview-GUI-Pfad weiterbauen, dann geometrisch geprüftes geneigtes RGB-Dachflächenmosaik.

### 2026-10-26 · DEV-INT-001 – Gemeinsame Main-Integrationsbasis
- **Ziel und Nutzerfreigabe:** Alle bisherigen *geprüften* Entwicklungsstände statt ständiger Wiederholung als gemeinsame Offline-Entwicklungsbasis unter `main` zur Verfügung stellen. Wörtliche Nutzerabsicht: `main` darf zur Ablage des neuen Programmstands dienen.
- **Quelle:** `feature/offline-human-report-approval` ab geprüftem Head `a32fbe26ffd609e09a2a79973b934ac893e33cec`. Alte `main`-Basis `e523a30dff0cb6a17fc8d287289cadb9cbde28d8` ist Vorfahr (4018 Commits, 0 behind); geplanter Übergang nicht erzwungener Fast-forward auf den final getesteten Integrationscommit. Die resultierende exakte SHA nach Ref-Update ist auf GitHub abzulesen.
- **Bereits implementierte technische Bereiche:** Offline-Windows-UI, lokale DJI-Import-/M3T-Parser, ORB-/RGB-Fotoregistrierung, Segmentvorschau, geneigte kalibrierungsgebundene Dachflächenkacheln, Projekt→2 RGB→PNG/JSON-Diagnostik, SQLite- und Expertenfreigabe-Gates.
- **Neu in diesem Schritt:** Dokumentationsbasierte Integrations-/Releasegates unter `docs/MAIN_INTEGRATION_BASELINE_2026-10-26.md`; README, Start-Here, Register, Entwicklungsvereinbarung, Handoff und Roadmap folgen `main` als neuer Quell-Basis. Keine zusätzliche ungeprüfte Laufzeitfunktion.
- **Quellen-Testevidenz:** SHA `a32fbe26ffd609e09a2a79973b934ac893e33cec`: [Python Tests](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40362304927) und [Windows](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40362304745), Python 3.11/3.12 grün. Der **zusätzliche Integrations-Dokumentationscommit** muss unabhängig grün sein, bevor `main` bewegt wird.
- **Status:** Git-Integration nach erneuter CI, **nicht** voll funktionsfähiges freigegebenes M3T-Orthofoto/Release. Lokaler alter Windows-Checkout unverändert.
- **Bewusst nicht pauschal gemergt:** die drei divergierten Zwei-Agenten-Experimentbranches; Datenschutztest-Befund und GUI-Teststand liegen in der aktiven Linie eigenständig vor; keine automatische PR-Schließung, kein `force`.
- **Nächster vertikaler Schritt:** sichtbare PySide6-UI zum Projekt-RGB-Preview mit Abbruch-/Qualitätsstatus, anschließend echte geneigte Dachflächen-Orthorektifizierung mit unabhängig geprüfter Intrinsic-/Pose-/Surveygeometrie.

### 2026-10-26 · DEV-INT-002 – Windows-CI auf neue Main-Integrationsbasis umstellen
- **Motiv:** Nach erfolgreich durchgeführtem `main`-Fast-forward von `e523a30dff` auf `56d6bf22f178bf98dbcb38559824d03c9ce718f1` war `.github/workflows/windows-offline.yml` auf `push` nur für den bisherigen Featurebranch konfiguriert. Ohne Anpassung würden zukünftige `main`-Pushs keine Windows-Offline-Prüfung starten.
- **Änderung:** Windows-Actions-Pushtrigger **additiv** um `main` ergänzen, Featurebranch-Auslöser für historische Vergleichbarkeit beibehalten; bestehende Windows-Testfälle unverändert. Python-`tests`-Workflow löst bereits auf allen Pushs aus und bleibt unverändert.
- **Validierung:** Ergänzter Test `tests/test_main_windows_ci_gate.py` bestätigt Workflow-Trigger für beide Zweige aus YAML-Text. Der exakte neue `main`-Commit muss erneut unter Python und Windows 3.11/3.12 grün sein.
- **Status:** Nur CI- und Anforderungsverwaltung, keine lokalen Dateimigrationen/Originaldaten/Produktivdatenbank, keine neue fachliche Orthofoto- oder Thermal-Freigabe.
- **Nächster Schritt:** vertikale offline PySide6 GUI-Anbindung des vorhandenen Projekt→2 RGB→PNG/JSON-Wegs auf geprüfter `main`-Basis; keine erneuten redundanten MPO-Metadatenprüfungen.

### 2026-10-26 · DEV-RGB-GUI-001 – Echter Projekt-RGB-Vorschauweg in PySide6
- **Branch / Start-HEAD:** `feature/offline-project-rgb-preview-gui` von `main` @ `00c576b12215be5462790198df7c5516efea5046`. Funktionale Commits: `1482dfd` (Projektpaar-/Abbruchservice), `aaa9bb4` (Worker/Bilddialog), `041f8a0` (Verarbeitungsseite), `0644ef5` (Shell), `f573694` (End-to-End-/Windows-Tests), `8b5047d` (Stubservice-Fail-Closed-Fix). Der spätere finale Dokumentations-/Integrations-HEAD ist auf GitHub zu ermitteln.
- **Nutzerziel / vertikaler Bedienweg:** Aktives Projekt öffnen → eindeutiges importiertes RGB-Nachbarpaar wählen → vorhandenen **leeren** Ausgabeverzeichnisordner ausdrücklich wählen → im eigenen QThread bereits vorhandene matcherbasierte Vorschau erzeugen → lokale PNG und JSON erstellen → PNG in sichtbar als **nichtmetrisch** gekennzeichnetem Qt-Dialog anzeigen. Abbrechen oder Projektwechsel verhindert veraltete Resultatanzeige.
- **Neue Dateien:** `gui/project_rgb_preview_worker.py`, `gui/project_rgb_preview_dialog.py`, `tests/test_gui_project_rgb_preview.py`.
- **Geänderte Dateien:** `services/rgb_project_preview_vertical.py`, `gui/processing_page.py`, `gui/shell.py`, `.github/workflows/windows-offline.yml`. Der Arbeitszweig ist ausdrücklich im Windows-CI-Pushtrigger enthalten, sodass **vor** einer Übernahme nach `main` Windows-Testläufe sichtbar sind.
- **Wiederverwendet statt neu erfunden:** bestehendes SQLite-Importmodell, `stitch_rgb_preview`, `save_rgb_preview_artifacts`, Pixel-/MPO-Primärbildvalidierung und Qt-Projekt-/Verarbeitungsseiten-Lifecycle. RGB-Nachbarpaarliste ist nur eine schnelle lesende SQLite-Abfrage nach 4-stelligen DJI-RGB-Bildnummern, **kein positiver Überlappungs- oder Geometrienachweis**.
- **Validierung:** neue synthetische Qt-End-to-End-Tests für Projektauswahl, echtes PNG/JSON, sichtbare Warnhinweise, unveränderte Originalbytes/PV-Modulanzahl, Abbruch vor Ausgabe, verspätete Ergebnisse nach Projektwechsel, fehlende oder fremde Projektservices. Vorherige 33 echten SC-0003-Aufnahmen wurden **nicht auf unserem GitHub-Runner verarbeitet**; reale lokale GUI-Abnahme bleibt ausstehend.
- **CI:** `tests` und `windows-offline-validation`, Python 3.11 und 3.12, müssen auf dem **finalen Dokumentationscommit** beide erfolgreich sein. Frühes `0644ef5`-Linux-Rot fand inkompatible vereinfachte Tests ohne `.database`; gezielter Fix `8b5047d` setzt das Feature bei diesen Services fail-closed. Noch kein positives Ergebnis des abschließenden Commit-SHA vorwegnehmen.
- **Abbruch-/Qualitätsgrenze:** kooperativer Abbruch an definierten Stellen; laufende OpenCV-Bildregistrierung nicht vorzeitig unterbrechbar, aber Qt bleibt bedienbar. Ausgaben in vorhandenen leeren Nutzerordner; keine Datenbank-Migration, Originalbildänderung oder automatisch bestätigte Module. Fehlgeschlagene/inkonsistente Paarregistrierung **kein** Mosaik; RANSAC-Inlier **kein** metrisches Orthofoto. Haus-/PV-Neigungen und echte Kamera-/Dachkalibrierung weiterhin offen; kein Thermal/°C/Review/Export-Gate verändert.
- **Freigabegrad:** synthetisch programm-/Windows-CI-testbare GUI-Integration, **keine persönliche Windows-10-Nutzerhardwareabnahme, keine echte SC-0003-Orthorektifizierung**. Nach finalem CI kontrollierter `main`-Fast-forward; vorher `main` unverändert lassen.
- **Nächster einzelner vertikaler Schritt:** Benutzergeprüften lokalen Windows-10-GUI-Pilot dieser Funktion mit SC-0003 ausführen; nur bei positivem Ergebnis eine eigenständige kalibrierte Dachflächenrekonstruktion mit unabhängiger Flächennormalen-/Pose-/Coverage-Evidenz ermöglichen. Kein erneuter MPO-/EXIF-/ORB-Inventurzyklus.

### 2026-10-26 · DEV-RGB-GUI-001 – Windows-Schließfehler beim Integrationsgate behoben
- **Beim realen GitHub-Windows-CI entdeckt:** Der frühe Build `8b5047d` hatte einen Windows-Startup-Smoke-Testfehler `WinError 32` beim Entfernen einer *temporären* `smoke.sqlite3`-Datei. Ursache: `with sqlite3.connect(...) as db` schließt im Python-`sqlite3`-API **nur die Transaktion, nicht die Verbindung**. Bei der neuen automatischen Projekt-RGB-Paarliste wurde nach jedem GUI-Refresh eine lesende Verbindung mit offenem Dateihandle erzeugt. Keine Änderung einer echten Nutzer-DB beobachtet.
- **Gezielter Fix:** `d8b59f8` verwendet `contextlib.closing(sqlite3.connect(...))` **für beide** read-only Service-Abfragen. Die Leserechte `mode=ro`, `PRAGMA query_only` und alle sonstigen Sperren bleiben erhalten; keine Tests abgeschwächt.
- **Regressionsprüfung:** `6da6889` ergänzt einen Windows-tauglichen Test, dass die von der RGB-Liste gelesene SQLite-Datei anschließend sofort gelöscht werden kann, ohne ein verbleibendes Handle. Außerdem end-to-end Qt-Dialog, Abbruch und Projektwechsel weiterhin kontrollieren. Der zusätzliche Dokumentationscommit muss das unveränderte Windows-Smoke-Gate erneut bestehen.

### 2026-10-26 · DEV-RGB-GUI-001 – CI-/Main-Abschluss bestätigt
- **Vollzogener Integrationsstand:** `main` und `feature/offline-project-rgb-preview-gui` am Fast-forward-Abschluss identisch auf `f1eaf5650ad7ad188afe22e93a61983bd040db44`. `main` wurde ohne Force-Push vom zuvor geprüften `00c576b12215be5462790198df7c5516efea5046` um **11 Commits** fortgesetzt. Featurebranch bleibt erhalten.
- **Finaler Code-CI-Nachweis für exakten `f1eaf565`:** [Python Tests 3.11/3.12 – success](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40370445214), [Windows 3.11/3.12 – success](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40370445459). Zusätzlicher Endtest prüft **sichtbaren Abbruchknopf** und keine PNG/JSON-Ausgabe bei Abbruch. Der initial gescheiterte Windows-Test wegen offenem SQLite-Dateihandle ist gezielt behoben, nicht übersprungen.
- **Abnahmegrenze:** 100% **automatisiert synthetischer Teststand**; nicht die reale Windows-10-Anwendung auf den Originalen von SC-0003 ausgeführt, keine eigenständig vermessene geneigte Dachfläche, kein freigegebenes Orthofoto, keine georeferenzierte Thermalansicht, kein Modul-/Defekt-/°C-Nachweis.
- **Folgechat:** Der neue Entwicklungsstand liegt **bereits auf `main`**. Nicht erneut Projekt-/MPO-Formate untersuchen und nicht dieselbe PySide6-Verbindung neu programmieren. Nächster Schritt: **kontrollierter lokaler Win10-Abnahmetest auf separatem Checkout**, danach kalibrierte Dachflächengeometrie. Dieser nachträgliche reine Dokumentationscommit wird unter `main` nochmals separat in CI geprüft.


### 2026-10-28 · ARCH-RGB-ORTHO-001 – Lizenzneutrales Orthofoto-first (Dokumentation, kein fertiger Worker)
- **Verbindliche Nutzerentscheidung:** Kein ODM, WebODM oder ODX integrieren, aufrufen, ausliefern oder deren Implementierung kopieren. Nur allgemeine Methoden/Verfahrensschritte als Architekturreferenz; zusätzliche Abhängigkeiten müssen einzeln lizenz-/offline-/Windows-10-geprüft werden.
- **Quelle:** [ORTHOFOTO_LICENSE_NEUTRAL_ARCHITECTURE_2026-10-28.md](ORTHOFOTO_LICENSE_NEUTRAL_ARCHITECTURE_2026-10-28.md).
- **Neu priorisierter vertikaler Pfad:** SC-0003 -> **ganze verfügbare RGB-Serie** -> globale Kamerarekonstruktion/BA und Surface-Modell -> geometrisch überprüftes RGB-Orthofoto plus geneigte modulparallele Flächenansichten -> PV-Modulpolygone/-IDs -> Thermalregistrierung. Einzelbild- und Paarvorschauen nur interne Diagnostik; keine weitere Hauptentwicklung für Zwei-Foto-Stitching.
- **Bestehender Code:** `odm_rgb_adapter.py` ist trotz historischem Namen nur lokales Staging ohne ODM-Aufruf. Lizenzneutral umbenennen, falls der Pfad berührt wird. Vorhandene Matcher/Geometrie-/Dachkachel-/GeoTIFF-Inspektion wiederverwenden; kein Doppelaufbau.
- **Status:** Architektur und Dokumentation, **nicht** neue SfM-/MVS-Engine implementiert und **kein** Orthofoto freigegeben. GitHub-Branch/Commit und CI nach Erzeugung des Commit einzeln prüfen; `main`, Nutzer-Windows-PC, Originalfotos und produktive SQLite unverändert. PR #7/#8 bleiben separate, ungemergte Entwürfe.
- **Nächste einzige Implementierungsaufgabe:** `DEV-RGB-ORTHO-ENGINE-001` – Projekt -> verfügbare gesamte RGB-Serie -> echtes globales Kameranetz/robuste Mehrbildgeometrie -> erster *zusammenhängender* dachbezogener RGB-Ausgabebereich mit Lücken-/Qualitätsstatus; bei fehlender Geometrie expliziter Sperrstatus statt vermeintlich vermessenem Orthofoto.


### 2026-10-28 · GOV-CONTINUITY-001 – Verbindlicher kompakter Chat-Checkpoint
- **Nutzerproblem:** Wiederholte Agentenwechsel haben bereits geprüfte Programmteile neu angefangen und die Orthofoto-first-Strategie durch Bildpaar-/Metadaten-Nebenentwicklungen unterbrochen. Veraltete Einstiege in README und sehr langen Archivdateien haben das begünstigt.
- **Lösung auf getrenntem Featurebranch PR #9:** `docs/AKTUELLER_ENTWICKLUNGSSTAND.md` als einziger **priorisierter aktueller** Einstiegsvertrag; README, `PROJECT_START_HERE.md`, Fachroadmap, Agreement und Archiv-Handoff mit Vorabverweisen; maschineller Link-/Pflichtkapiteltest. Das PDF bleibt privat und wird nicht nach GitHub hochgeladen.
- **Evidenz:** Tatsächlicher `main@5f2de8f`-Stand; PR #7/#8/#9 offen, ihre Python-/Windows-Prüfungen für die zuvor überprüften Commits grün; echte SC-0003-Win10-GUI und Nahtqualitätsfehler; kein vollständiges Orthofoto.
- **Status:** Übergabemechanismus/Arbeitsorganisation, keine neue Photogrammetrie-Engine oder echte Nutzerhardwareabnahme. CI des neuen Abschlusscommits separat prüfen; `main` unberührt.
- **Nächste Aufgabe:** ausschließlich `DEV-RGB-ORTHO-ENGINE-001` aus dem aktuellen Checkpoint; Checkpoint zuallererst vor nächstem Chat aktualisieren, keine erneute Metadaten-/MPO-/Pair-Tests.


### 2026-10-28 · DEV-RGB-ORTHO-ENGINE-001 – Erste durchgängige Projektserie → echte Dachflächenkacheln
- **Branch:** `feature/orthofoto-license-neutral-rgb-first-20261028`, vorheriger Übergabecommit `2de74ca5`, Implementierungscommit `36e3b25e`. PR #9 bleibt Draft, `main` unverändert.
- **Vertikaler technischer Nutzerweg:** explizit selektiertes SQLite-Projekt → **alle** importierten DJI-RGB-Primärbilder, keine Zwei-Paar-Auswahl → externes kalibriertes JSON-Bundle, pro Frame Intrinsics, Distortion, Pose und ENU-Kamera; externe gemessene Dachfläche und pro Frame mindestens vier räumlich unabhängige Kontrollpunkte → geometrisches Fail-Closed-Gate aus PR #8 → vorhandener `render_rgb_surface_tile()` pro Quelle und Kachel → lokale RGB-PNG-Kacheln + Gültigkeitsmasken + Qualitäts-/Abdeckungsmanifest, rein lesend gegen Original und SQLite. CLI: `python -m mcm_solarcheck.services.rgb_project_roof_cli --database ... --project-id ... --geometry-json ... --output-dir ...` (Pfad mit leerem Ordner).
- **Code:** `src/mcm_solarcheck/services/rgb_project_roof_vertical.py`, `rgb_project_roof_cli.py`; gezielt übernommene und zusätzlich CI-geprüfte Kontrollpunktimplementierung `rgb_roof_control_point_gate.py` aus PR #8. Synthetische ganze RGB-Projektserie mit 3 JPEGs und SQLite, Echtkacheln und Masken, keine Seiteneffekte, Kontrollpunktmismatch, fehlende Kalibrierung, kooperativer Abbruch getestet.
- **Grenzen:** Externes Geometry-JSON für SC-0003 fehlt. Kein automatisches SfM/Bundle Adjustment, kein photogrammetrisch vermessenes Orthofoto/CRS, keine Prüfung echter Survey-Provenienz oder private Bilddaten in GitHub, kein UI-Button, keine PV-/Thermal-/Fachfreigabe. Nur bereits vorhandenes cv2/NumPy verwendet, keine ODM/WebODM/ODX-Komponente, keine Neuinstallation.
- **Evidenz/CI:** Neue Python-/Windows-3.11/3.12-CI für exakt letzten Dokumentationscommit nachlaufen lassen; vorherige grüne PR9-Läufe dürfen nicht als Ergebnis dieser Implementierung ausgegeben werden. Keine reale Windows-10-Hardwareabnahme dieses neuen Pfades.
- **Einzige nächste Entwicklungsaufgabe:** gemeinsame bildübergreifende Feature-Tracks, globaler Kalibrierungs-/Pose-/Bundle-Adjustment-Prozess über **alle** Projektbilder; daraus belastbares kamerageometrisches Paket für den bereits laufenden Dachkachelpfad. Kein erneuter MPO-/EXIF-/ORB-Inventurlauf und keine isolierte Zwei-Bild-Vorschau.
