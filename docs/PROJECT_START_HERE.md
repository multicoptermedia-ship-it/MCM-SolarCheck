# START HERE – SolarCheck Folgechat und Entwicklungsübernahme

**Stand 26.10.2026. Ein neuer Chat muss zuerst die tatsächlichen Repository-Dateien lesen, nicht aus einer alten Chat-Zusammenfassung programmieren.** Verbundener GitHub-Branch: `feature/offline-human-report-approval`; `main` ist historisch und führt beim Inventur-Snapshot keine lauffähige Anwendung.

1. [REPOSITORY_BRANCH_INVENTORY_2026-10-26.md](REPOSITORY_BRANCH_INVENTORY_2026-10-26.md) – **alle 14 Branches, PR-/CI-/Differenzen, Nutzerbelege und Gaps**.
2. [DEVELOPMENT_STEP_REGISTER.md](DEVELOPMENT_STEP_REGISTER.md) – **Pflichtregister für jeden abgeschlossenen Entwicklungsschritt**, inklusive Tests/Belege/Gates und Übergabe.
3. [DEVELOPMENT_AGREEMENT.md](DEVELOPMENT_AGREEMENT.md) – vollständige technische und rechtliche Vereinbarungen.
4. [CHAT_HANDOFF.md](CHAT_HANDOFF.md) – ausführliche frühere Entscheidungen und Nutzerumgebung.
5. [PV_ORTHOMOSAIC_FIRST_ROADMAP.md](PV_ORTHOMOSAIC_FIRST_ROADMAP.md) – RGB-first, echte geneigte Dach-/Modulflächen und erst spätere Thermalregistrierung.

**Derzeit letzter realer Nutzertest:** 33/33 originale RGB-MPO (4000×3000 Hauptbild + 960×720 Begleitbild), 160 Thermal in getrenntem TEST-Projekt Hummintech3; 28/32 plausible ORB-Nachbarlinks, 4 kritische, fünf Querlinks unzureichend; DJI Gimbalwinkel-Metadaten eingeordnet. **Nicht erneut** nach denselben PowerShell-Ausgaben fragen.

**Letzte implementierte vertikale Funktion:** GitHub-Stand `0a29e6a`: testprojektspezifische 2-RGB-Originale→begrenztes diagnostisches PNG/JSON; mit synthetischen Tests/CI, noch nicht in alter Windows-10-GUI installiert. **Nächster Schritt:** nutzbaren GUI-Aufruf mit sicheren Status-/Abbruch-/Exportgates herstellen. Nur bei unabhängiger tatsächlicher Kamerakalibrierung + Dachsurvey darf ein überprüftes Oberflächen-RGB-Orthofoto entstehen.

**Schutz:** Niemals Originalbilder, produktive SQLite, Nutzerbackups, `main`, offene PRs oder andere Branches ohne ausdrückliche Freigabe verändern. GitHub-Codecommit aktualisiert **nicht** den lokalen alten Windows-Checkout. Keine fiktive °C-/Defekt-/Vermessungs-/Fachfreigabe.

**Bei jedem Abschluss:** diesen Startpunkt prüfen, Register + Entwicklungsvereinbarung + Chat-Handoff und thematische Roadmap aktualisieren, danach CI des finalen Commits prüfen. Benutzer erhält eine kurze, nachvollziehbare Ergebnisübergabe.
