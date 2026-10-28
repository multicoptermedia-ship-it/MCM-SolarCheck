# START HERE – SolarCheck Folgechat und Entwicklungsübernahme

**Stand 26.10.2026. Ein neuer Chat muss zuerst die tatsächlichen Repository-Dateien lesen, nicht aus einer alten Chat-Zusammenfassung programmieren.** **Neuer gemeinsamer Entwicklungsstand:** `main` nach dem nicht erzwungenen CI-geprüften Fast-forward; Quelle des Ausgangsstands: `feature/offline-human-report-approval`. **Nur Integrationsbasis – kein lokal abgenommenes Release.** Die Branch-Bestandsaufnahme beschreibt ausdrücklich den **früheren Stichtag** vor dem Fast-forward.

1. [MAIN_INTEGRATION_BASELINE_2026-10-26.md](MAIN_INTEGRATION_BASELINE_2026-10-26.md) – **Main-Übernahme, integrierte Softwarebereiche und offene Windows-/RGB-/Thermal-Gates**.
2. [REPOSITORY_BRANCH_INVENTORY_2026-10-26.md](REPOSITORY_BRANCH_INVENTORY_2026-10-26.md) – **alle 14 Branches, PR-/CI-/Differenzen, Nutzerbelege und Gaps**.
3. [DEVELOPMENT_STEP_REGISTER.md](DEVELOPMENT_STEP_REGISTER.md) – **Pflichtregister für jeden abgeschlossenen Entwicklungsschritt**, inklusive Tests/Belege/Gates und Übergabe.
4. [DEVELOPMENT_AGREEMENT.md](DEVELOPMENT_AGREEMENT.md) – vollständige technische und rechtliche Vereinbarungen.
5. [CHAT_HANDOFF.md](CHAT_HANDOFF.md) – ausführliche frühere Entscheidungen und Nutzerumgebung.
6. [PV_ORTHOMOSAIC_FIRST_ROADMAP.md](PV_ORTHOMOSAIC_FIRST_ROADMAP.md) – RGB-first, echte geneigte Dach-/Modulflächen und erst spätere Thermalregistrierung.

**Derzeit letzter realer Nutzertest:** 33/33 originale RGB-MPO (4000×3000 Hauptbild + 960×720 Begleitbild), 160 Thermal in getrenntem TEST-Projekt Hummintech3; 28/32 plausible ORB-Nachbarlinks, 4 kritische, fünf Querlinks unzureichend; DJI Gimbalwinkel-Metadaten eingeordnet. **Nicht erneut** nach denselben PowerShell-Ausgaben fragen.

**Letzter neu implementierter Vertikalschritt:** [DEV-RGB-GUI-001](DEVELOPMENT_STEP_REGISTER.md) – offline Projekt → bereits importiertes RGB-Nachbarpaar → leerer lokaler Ausgabeordner → QThread-Diagnose-PNG/JSON → sichtbarer Qt-Vorschaudialog samt Abbruch. **Der Code ist bereits nach nachweislich grünen Python- und Windows-CI-Gates in `main` integriert (Code-SHA `f1eaf5650ad7ad188afe22e93a61983bd040db44`).** Die alte lokale Windows-10-GUI wurde noch nicht aktualisiert oder auf SC-0003 ausgeführt. **Nächster Schritt:** echte Windows-10-Abnahme des neuen GUI-Pfads und danach unabhängig kalibrierte geneigte RGB-Dachflächengeometrie; keine metrische Orthofoto-Freigabe aus der nichtmetrischen Vorschau.

**Schutz:** Niemals Originalbilder, produktive SQLite, Nutzerbackups, `main`, offene PRs oder andere Branches ohne ausdrückliche Freigabe verändern. GitHub-Codecommit aktualisiert **nicht** den lokalen alten Windows-Checkout. Keine fiktive °C-/Defekt-/Vermessungs-/Fachfreigabe.

**Bei jedem Abschluss:** diesen Startpunkt prüfen, Register + Entwicklungsvereinbarung + Chat-Handoff und thematische Roadmap aktualisieren, danach CI des finalen Commits prüfen. Benutzer erhält eine kurze, nachvollziehbare Ergebnisübergabe.

**CI-Integration:** `main` wurde nach GitHub-CI-Grün per Fast-forward an den bisherigen Entwicklungsstand angeglichen. [DEV-INT-002](DEVELOPMENT_STEP_REGISTER.md) dokumentiert den neuen Windows-Pushtrigger für `main`. Ziel weiterhin **Entwicklung**, kein freigegebener Offline-Release.


## 28.10.2026 – Verbindliche Lizenz- und Orthofoto-Priorität
**Neuer Primärplan:** [ORTHOFOTO_LICENSE_NEUTRAL_ARCHITECTURE_2026-10-28.md](ORTHOFOTO_LICENSE_NEUTRAL_ARCHITECTURE_2026-10-28.md). **Kein** ODM/WebODM/ODX als Code, Bibliothek, Dienst, Container, Prozess oder Produktbestandteil; nur allgemeine methodische Orientierung. Vollständige verfügbare RGB-Flugbildserie -> eigene lizenzneutral entwickelte Mehrbild-Photogrammetrie -> geprüfte RGB-Orthofotos und geneigte PV-Flächenansichten -> erst dann Modul-Erkennung, -ID, Thermalzuordnung. Der historische nächste Schritt „RGB-Paarvorschau“ ist inzwischen real getestet, mit mangelhafter Naht, und **nicht** erneut als Hauptaufgabe zu entwickeln. PR #7 und #8 sind separate Vorarbeiten. `main` bleibt bis zum expliziten Integrationsauftrag unberührt.
