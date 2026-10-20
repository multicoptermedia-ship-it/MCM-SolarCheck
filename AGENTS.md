# MCM-SolarCheck: befristeter Zwei-Agenten-Pilot

Diese Datei gilt **nur auf diesem experimentellen Branch**. Sie ändert nicht die verbindlichen Entwicklungsregeln auf dem Haupt-Entwicklungsbranch.

- Rolle: Agent A – Implementierung.
- Aufgabe: https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/issues/5
- Implementiere ausschließlich den im Issue #5 beschriebenen Qt-Datenschutz-Fix. Code-Eigentum: src/mcm_solarcheck/gui/shell.py; nur eigene kleine Tests falls unbedingt nötig. Nicht den Testpfad von Agent B bearbeiten.
- Lies vor jeder Änderung docs/DEVELOPMENT_AGREEMENT.md und docs/CHAT_HANDOFF.md. Ergänze deren dauerhafte Regeln nicht eigenmächtig.
- Behalte den vertikalen Offline-Windows-Prozess, SQLite-Transaktionen, Projekttrennung, Datenschutz, Freigabe-Gates und Originaldateischutz bei.
- Keine Netzwerktelemetrie, kein Kundenbild-Upload, keine automatischen Experten-/Berichtsfreigaben.
- Schreibe niemals in main, feature/rgb-all-segments-export oder die offene PR-Integrationsbasis. Nur dieser Branch ist beschreibbar.
- Keine Merge-/PR-Aktion ohne Integrationsreview. Liefere einen reproduzierbaren Diff, Tests auf Python 3.11/3.12, bekannte Risiken und Ausführungsdetails.
- Integration und fünf aufeinanderfolgende Entwicklungsschritte bleiben zentrale Verantwortung; der fünfte Commit aktualisiert bei einem späteren freigegebenen Integrationsblock gemeinsam beide Übergabedokumente.
- Zwei-Agenten-Verfahren **nur ausprobieren**, noch keine Regel als dauerhaft annehmen; dafür müssen Unabhängigkeit, Qualität, Integration, Gesamt-CI und Zeit-/Kostenvergleich nachweislich erfolgreich sein.
