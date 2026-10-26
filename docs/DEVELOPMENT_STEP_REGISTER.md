# Verbindliches Entwicklungsregister – MCM-SolarCheck

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
