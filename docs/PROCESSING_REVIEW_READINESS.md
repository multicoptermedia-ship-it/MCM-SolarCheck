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
