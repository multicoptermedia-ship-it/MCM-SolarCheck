# Repository-Bestandsaufnahme und Branch-Katalog – 26.10.2026

**Status:** Verbindliche Inventur-/Wissensbasis; keine Codeintegration, keine Releasefreigabe. **Repository:** `multicoptermedia-ship-it/MCM-SolarCheck`. **Inventur-Snapshot:** 26.10.2026, vor diesem Katalog-Commit; aktiver Entwicklungs-HEAD `0a29e6a66d2ca0b23962f50b09ce099a2decaf5a`. **Default-Branch:** `main`.

## Wichtige Anweisung für Folgechats

**VOR einer neuen Entwicklung stets lesen:** [PROJECT_START_HERE.md](PROJECT_START_HERE.md), diesen Katalog, [DEVELOPMENT_STEP_REGISTER.md](DEVELOPMENT_STEP_REGISTER.md), [DEVELOPMENT_AGREEMENT.md](DEVELOPMENT_AGREEMENT.md), [CHAT_HANDOFF.md](CHAT_HANDOFF.md) und bei PV-Geometrie [PV_ORTHOMOSAIC_FIRST_ROADMAP.md](PV_ORTHOMOSAIC_FIRST_ROADMAP.md). Bereits erledigte lokale Nutzer- und CI-Prüfungen nicht als ungeschehen behandeln. Nur neue entscheidungsrelevante Tests anfordern. Diese Dateien im selben Branch dauerhaft aktualisieren.

## Untersuchungsmethode und Grenzen

- GitHub REST: **alle 14 am Stichtag gelisteten Branch-HEADs** erfasst, aktuellen HEAD-Commit und Commitdatum/-titel für jeden geprüft, vollständigen rekursiven Git-Baum für jeden gelesen (`truncated=false`), alle 14 mit `main` und 13 ältere Branches mit aktivem Arbeitszweig per Git-Vergleich eingeordnet; jüngsten GitHub-Actions-Lauf je Branch HEAD geprüft.
- `main` und `images` zeigen auf **dieselbe SHA**. Alle anderen Branches sind hinter/gegen den aktiven Branch einzuordnen. Die drei `experiment/two-agent-*` Branches sind **divergiert** und besitzen exklusive Commits. Alle übrigen älteren Branches sind **vollständig Vorfahren** des aktuellen Arbeitszweigs. Das betrifft Commit-Abstammung, nicht automatisch identische Laufzeitsemantik.
- GitHub-Compare begrenzt die Dateiliste bei großen Diffs auf die ersten **300 Einträge**. Die Zahlen der vorhandenen Dateien stammen daher aus den ungekürzten **Git-Bäumen**, nicht aus einer möglicherweise gekürzten Compare-Dateiliste. Die Commit-Abstände sind Git-Metadaten, kein Qualitätsmaß.
- CI-Grün bedeutet nur die jeweilige **damalige** Testsuite am jeweiligen Commit, kein Hardwaretest des Benutzers, keine unabhängige Vermessung, keine reale 33-Bild-Orthofoto-Freigabe. Für viele Altzweige gibt es nur den `tests`-Workflow, nicht den aktuellen Windows-Workflow.
- Keine Branches gelöscht, neu erstellt, gemergt oder umgebased. Die offenen Pull Requests #3 und #4 bleiben offen. Kein lokales Foto oder SQLite in Git hochgeladen.

## Executive Facts

| Punkt | Feststellung |
|---|---|
| Branches am Stichtag | **14**, davon **13 unterschiedliche HEAD-SHAs** |
| `main` | Nur **5 Dateien**, kein `src/`, `tests/` oder `docs/` in diesem Snapshot; **nicht** der lauffähige Entwicklungsstand |
| `images` | SHA-identisch zu `main` |
| Aktiver Branch | `feature/offline-human-report-approval` – **1460 Dateien** (618 `src/`, 629 `tests/`, 177 `docs/`; weitere Konfigurationen/Skripte) |
| Git-Abstammung | 10 weitere Nicht-Experiment-Branches liegen vollständig auf der Vorgeschichte des aktiven Branches; drei Experimente haben divergente Commit-Spitzen |
| Aktiver CI vor Inventur | `tests` und `windows-offline-validation` jeweils **grün** auf Python 3.11/3.12, SHA `0a29e6a` |
| Offene PRs | #3 `integration/phase10-master` → `main`; #4 `feature/unified-online-offline-foundation` → `integration/phase10-master` |

**Hinweis zur Zählung:** Die **10 anderen Nicht-Experiment-/Nicht-Aktiv-Branches insgesamt** sind Git-Vorfahren des Arbeitszweigs, darunter `main` und `images` mit identischer SHA. Die **anderen acht** sind eigenständige ältere Entwicklungs- oder Releasezweige. Die drei experimentellen Branches sind divergiert.

## Katalog aller 14 Branches (unveränderter Stichtags-HEAD)

| Branch | SHA kurz | HEAD-Datum | Dateien | Relation zum Arbeitszweig | CI am HEAD |
|---|---|---|---:|---|---|
| `main` | `e523a30df` | 11.09. | 5 | Vorfahr, Default | kein Lauf |
| `images` | `e523a30df` | 11.09. | 5 | identisch mit `main` | kein Lauf |
| `feature/m3t-importer-foundation` | `69861d6d9` | 15.09. | 11 | Vorfahr | kein Lauf |
| `ci/cadence-integration-check` | `588c56602` | 22.09. | 157 | Vorfahr | `tests` grün |
| `release/windows-offline-installer` | `7fa19862c` | 25.09. | 280 | Vorfahr | `tests` grün |
| `feature/m3t-radiometric-parser` | `33840f019` | 02.10. | 453 | Vorfahr | `tests` grün |
| `integration/phase10-master` | `bb943f1b9` | 08.10. | 523 | Vorfahr, PR #3 offen | `tests` grün |
| `feature/unified-online-offline-foundation` | `dfb166890` | 13.10. | 1070 | Vorfahr, PR #4 offen | `tests` grün |
| `feature/block38-offline-ai-ingestion-tests` | `a9589cbef` | 18.10. | 1218 | Vorfahr | `tests` grün |
| `experiment/two-agent-export-qa` | `2f631ece1` | 20.10. | 1296 | divergiert, 2 exklusive Commits | **`tests` rot** |
| `experiment/two-agent-export-ui` | `b6e9fdb12` | 20.10. | 1295 | divergiert, 2 exklusive Commits | `tests` grün |
| `experiment/two-agent-integration-review` | `549f73797` | 20.10. | 1295 | divergiert, 1 exklusiver Commit | `tests` grün |
| `feature/rgb-all-segments-export` | `ac240e98c` | 21.10. | 1312 | Vorfahr | `tests` grün |
| `feature/offline-human-report-approval` | `0a29e6a66` | 26.10. | 1460 | **aktiver Arbeitszweig / Snapshot** | `tests` + **Windows** grün |

Git-Historienrelation wurde jeweils mit `compare(base=<Branch>, head=feature/offline-human-report-approval)` überprüft. Bei den drei Experimentzweigen liegt der gemeinsame Vorfahr `db6762949` (kurz) und die aktive Linie ist gegenüber diesem Vorfahren weiterentwickelt; ihre zusätzlichen Experimente sind nicht durch einen Merge dieses Branches integriert.

## Erkenntnisse und Wiederverwendung je Zweig

1. **`main` / `images`:** Nur früher Architektur-Basispunkt; keine lauffähigen Offline-Module auf diesem Git-Stand. Bloßer Branchname `main` darf nicht als neueste SolarCheck-Software interpretiert werden. Beide Heads identisch; nicht mergen, um angeblich neuere Funktionen zu erhalten.
2. **`feature/m3t-importer-foundation`:** Erste DJI-M3T-Domänen-/Import-/Paarungsbausteine und Thermalformat-Notizen. 5 Quelldateien/0 Tests; vollständig in aktiver Geschichte. Importer nicht von Grund auf neu entwerfen.
3. **`ci/cadence-integration-check`:** Frühe Modulraster-/Cadence-Validierung, Robustheit numerischer Regressionen und echte M3T-Forschung. 68 Tests im damaligen Baum; von aktiver Linie übernommen. Zelllinien nicht als einzelne PV-Modulgrenzen bestätigen.
4. **`release/windows-offline-installer`:** Historische Windows-Offline-Auslieferungs-/Installations-Gates. Alter Releasezweig und grüner damaliger Test ersetzen keine aktuelle Windows-Hardwareabnahme. Keine unbekannte lokale Installation oder `main`-Merge.
5. **`feature/m3t-radiometric-parser`:** Radiometrischer 16-Bit-M3T-Pfad und Sensor-/Pairing-Qualitätskontrollen; Kalibrierung zu °C bleibt **getrennt belegt**. Dessen vorhandene Parser wiederverwenden.
6. **`integration/phase10-master`:** Frühere umfangreiche Integrationsbasis. PR #3 nach `main` ist offen, obwohl der aktive Branch deren Geschichte bereits enthält. Keine automatische PR-Ausführung.
7. **`feature/unified-online-offline-foundation`:** Breite Architekturarbeit zu gemeinsamen Oberflächen/Services, getrennten Online-/Offline-Gates und Staging. PR #4 offen; auf aktiver Linie bereits historisch enthalten. Cloud-/MariaDB-Komponenten nicht zu einer Offline-Betriebsabhängigkeit machen.
8. **`feature/block38-offline-ai-ingestion-tests`:** AI-Ingestion, Reviews und Exportgates; kein automatisch freigegebenes KI-Modul-/Defektergebnis. Die tatsächliche Aufsicht/Kontrolle bleibt notwendige Schranke.
9. **`experiment/two-agent-export-qa`:** Unabhängige Export-Datenschutz-QA entdeckte am HEAD einen konkreten Fehler: die Fehlermeldung einer bestehenden Exportzieldatei zeigte einen **privaten Dateipfad/Kundennamen**. Der Python-3.11-CI-Lauf war rot; Python 3.12 dort abgebrochen. Branch enthält `AGENTS.md` und unabhängigen `tests/test_pilot_export_error_privacy.py`; nicht unbesehen mergen oder als grün beschreiben.
10. **`experiment/two-agent-export-ui`:** Separater, im damaligen CI grüner GUI-Fix zur Unterdrückung privater Pfade in Exportfehlern. Exklusive Branch-Commits bleiben git-technisch divergent; nicht rückwärts mergen.
11. **`experiment/two-agent-integration-review`:** Ein Integrationsreview-Commit mit GUI-Fix und unabhängigem Privacy-Test; damalige CI grün. Aktiver Branch besitzt inzwischen eine weiterentwickelte `shell.py` und `tests/test_pilot_export_error_privacy.py`, beide **nicht SHA-identisch** mit den Experimentdateien. Inhaltliche Deckung wird durch eigene Tests/Review nachgewiesen, **nicht** durch behauptete Commit-Identität.
12. **`feature/rgb-all-segments-export`:** Existierende begrenzte **nichtmetrische** RGB-Flugsegmentregistrierung und -Vorschauen. Kernservices `flight_rgb_link_run.py`, `flight_rgb_geometry_chain.py`, `flight_rgb_all_segments.py` in aktiver Linie bereits vorhanden. Darauf aufbauen, keine Doppelimplementierung von ORB-Stitches.
13. **`feature/offline-human-report-approval`:** Aktiver Entwicklungszweig mit 629 Testdateien, 618 Quelldateien, drei GitHub-Workflows (am Snapshot). Fortgeschrittene Offline-Windows-Anwendung, Review-/Report-Gates, echte RGB-/M3T-Testdiagnostik, geneigte metrische Dachkacheln unter externer Kalibrierung, Thermal-Rohwerttests und neuer `rgb_project_preview_vertical.py` + CLI. GitHub-CI am Snapshot unter Windows/Python 3.11/3.12 erfolgreich; **neuer Projekt→Bild→PNG-Pfad nur synthetisch getestet, nicht lokal auf 33 M3T-Bildern installiert/geprüft**.

## Fachliche Nutzerbelege, bereits vor dieser Inventur erhoben

- Testprojekt **`SC-0003 · Hummintech3`** in der isolierten TEST-SQLite: interne Projekt-ID `sc-0f0ec1feb79c444fbe3ff22bab900a4e`; 33/33 RGB-Originale vorhanden, 4000 × 3000, 160 Thermal-Datensätze.
- **33 MPO-Dateien** mit zwei RGB-Teilbildern: primär **4000 × 3000**; Zweitbild **960 × 720**. Tatsächlich in Windows mit Pillow gesichtet. EXIF Brennweite **4,4 mm**, Kleinbildäquivalent **24 mm**. Verifizierte Objektivverzeichnungs-/Intrinsics-Daten **nicht gefunden** (`DewarpData`, `CalibratedOpticalCenterX/Y`, `CalibratedFocalLength` nicht vorliegend).
- **28/32** direkt benachbarte RGB-Bildpaare erfüllen den damaligen ORB-Matcher-Grenzwert, **4/32** (0130→0131, 0131→0132, 0132→0133, 0133→0134) nicht. Fünf geprüfte Überbrückungen waren bei 2,0–7,7% Inlier-Anteil ebenfalls nicht freigegeben. Inlier-Anteil **kein** Flächenüberlappungs-Prozentsatz; 0132→0133 räumlich nur 26,6% Breite der Inlierpunkte.
- Flugmetadaten zu diesen Bildern: Aufnahmeabstand rund 1,4–1,5 s und ca. 2 m GPS; Gimbal-Pitch rund −90°; scheinbare Roll/Yaw ±180°-Darstellungswechsel 0131–0133 bei nahezu konstanter Fluglage; keine ungeprüfte 180°-Bilddrehung. EXIF-Orientation 1, GimbalReverse 0.
- Die Zahl 33 RGB vs. 160 Thermal folgt **aus begrenzter Übergabe für den Test**, nicht aus einer dokumentierten Lücke der ursprünglichen Befliegung. Spätere zusätzliche RGB-Dateien möglich, ohne bestehende Datensatzinterpretation umzudeuten.
- Geneigte Dächer/Freiflächenmodule (häufig 20–30° Aufständerung) nur mit **echtem Dach-/Modulnormalenvektor**, korrekter Oberflächenentzerrung, unabhängiger Kalibrierung/Survey. Nadir zum Erdboden ist nicht senkrecht zur geneigten Modulfläche.
- Diese Nutzerbelege sind **konkrete lokale Beobachtungen aus Chat/PowerShell**, nicht in GitHub reproduzierte Bildläufe. **Keine privaten Originale, Pfade oder Kundeninformationen in CI/Git.**

## Aktuelle technische Gates und Prioritäten

**Geschützt:** produktive Nutzer-SQLite, separate Test-SQLite, private Originalaufnahmen und Sicherungen; keine Online-/ODM-/Docker-Abhängigkeiten ohne Freigabe; kein automatischer `main`-Merge/Branchlöschung; kein behauptetes Grad-Celsius, Defekt oder Experten-Review ohne Rohwert-, Kalibrierungs- und Freigabegates.

**Primärziel:** **vertikale RGB-first Entwicklung**: ausgewähltes Testprojekt → seine originalen RGB-Frames → begrenzte sichtbare, als **nichtmetrisch** markierte Vorschau → unabhängige Kamerakalibrierung/Surveydachebene → maßhaltige lokale RGB-Dachflächenansicht mit Coverage/Residuengates → erst danach Thermalregistrierung/Module. Die nichtmetrische Vorschau nicht als Geometrieersatz freigeben. Keine wiederholten MPO-/EXIF-/Metadaten-Tests ohne neuen technischen Grund.

**Explizite noch offene Arbeiten:** Windows-GUI-Anbindung des neuen Projekt-RGB-Vorschauwegs, echter reproduzierbarer SC-0003-Durchlauf der neuen implementierten Funktionen unter Kontrolle des Benutzers, verifizierte Camera Intrinsics/Extrinsics und geneigte Dach-/Modulflächen, mehrteilige Bildregistrierung/Gesamtdeckung, später Thermal-/Modul-Workflow.

**Governance:** [DEVELOPMENT_STEP_REGISTER.md](DEVELOPMENT_STEP_REGISTER.md) ist das verpflichtende, fortlaufende Register. Ein Entwicklungsschritt ist erst abgeschlossen, wenn Code/Test/CI/Begrenzungen/Status und Querverweise dort eingetragen wurden; Dokumentationsänderungen auf demselben Branch müssen danach noch selbst durch CI laufen. PDF-Berichte sind lesbare Snapshots; **Markdown im Git-Repository ist die wartbare Quelle der Wahrheit**.

## Verifizierbare GitHub-Quellen

- [Branches](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/branches), [aktueller Arbeitszweig](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/tree/feature/offline-human-report-approval), [PR #3](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/pull/3), [PR #4](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/pull/4).
- [Aktiver CI vor Inventur](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions), [roter Experiment-QA-Lauf](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/39452059534).
- Einzel-HEADs siehe Tabelle. Branchdaten sind zeitbezogen; **vor zukünftigen Schreiboperationen HEAD und CI immer neu prüfen**.

## Nachtrag vom 26.10.2026 – späterer Integrationsauftrag

Diese Inventur beschreibt weiterhin **den Branchzustand VOR der Integration** und die damaligen 14 Heads. Danach hat der Nutzer ausdrücklich gestattet, den dokumentierten, CI-geprüften aktiven Entwicklungsstand als gemeinsame Quellcodebasis per **Fast-forward in `main`** zu übernehmen. Maßgeblich für spätere Arbeiten ist [MAIN_INTEGRATION_BASELINE_2026-10-26.md](MAIN_INTEGRATION_BASELINE_2026-10-26.md) und [DEV-INT-001](DEVELOPMENT_STEP_REGISTER.md). **Die historische Branch-Tabelle oben nicht rückwirkend umschreiben.**
