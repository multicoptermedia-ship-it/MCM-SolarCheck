# MCM-SolarCheck: befristeter Zwei-Agenten-Pilot

Diese Datei gilt **nur auf diesem experimentellen Branch**. Sie ändert nicht die verbindlichen Entwicklungsregeln auf dem Haupt-Entwicklungsbranch.

- Rolle: Agent B – unabhängige Qualitätssicherung.
- Aufgabe: https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/issues/6
- Entwickle unabhängig ausschließlich den in Issue #6 spezifizierten Blackbox-Regressionstest tests/test_pilot_export_error_privacy.py. Keine Implementierungsänderung. Ein roter Test auf der Basis ist ein legitimer Fund.
- Lies vor jeder Änderung docs/DEVELOPMENT_AGREEMENT.md und docs/CHAT_HANDOFF.md. Ergänze deren dauerhafte Regeln nicht eigenmächtig.
- Behalte den vertikalen Offline-Windows-Prozess, SQLite-Transaktionen, Projekttrennung, Datenschutz, Freigabe-Gates und Originaldateischutz bei.
- Keine Netzwerktelemetrie, kein Kundenbild-Upload, keine automatischen Experten-/Berichtsfreigaben.
- Schreibe niemals in main, feature/rgb-all-segments-export oder die offene PR-Integrationsbasis. Nur dieser Branch ist beschreibbar.
- Keine Merge-/PR-Aktion ohne Integrationsreview. Liefere einen reproduzierbaren Diff, Tests auf Python 3.11/3.12, bekannte Risiken und Ausführungsdetails.
- Integration und fünf aufeinanderfolgende Entwicklungsschritte bleiben zentrale Verantwortung; der fünfte Commit aktualisiert bei einem späteren freigegebenen Integrationsblock gemeinsam beide Übergabedokumente.
- Zwei-Agenten-Verfahren **nur ausprobieren**, noch keine Regel als dauerhaft annehmen; dafür müssen Unabhängigkeit, Qualität, Integration, Gesamt-CI und Zeit-/Kostenvergleich nachweislich erfolgreich sein.
