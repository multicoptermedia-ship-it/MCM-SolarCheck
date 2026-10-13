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
