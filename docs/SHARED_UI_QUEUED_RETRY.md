# Wartende Aufträge erneut prüfen und anstoßen

Die Online-API `POST /api/compute-job-start?project_id=…&job_id=…` verwendet die angemeldete Sitzung, den Customer-Entry-Gate und den vorhandenen `ComputeJobService.get(..., user_id=…, project_id=…)`. Nur ein tatsächlich wartender Auftrag wird erneut durch die Kapazitätszulassung geschickt; abgeschlossene oder bereits laufende Aufträge werden nicht neu gestartet. Die Antwort gibt den gespeicherten Auftragsstatus wieder.

Die gemeinsame Browseroberfläche merkt sich den zuletzt erzeugten Auftrag im **Tab-Sitzungsspeicher** und stellt ihn nach einem Neuladen erst dann wieder her, wenn die Projektliste des aktuell angemeldeten Kunden geladen wurde. Die Speicherung im Browser ist lediglich ein unverbindlicher Hinweis, keine Berechtigung. Jede Statusabfrage und jeder erneute Start wird serverseitig geprüft. Beim Wechsel des Projekts wird der Hinweis gelöscht.

**Grenzen:** Das ist noch keine automatische Hintergrundwarteschlange, keine automatische Verarbeitung wartender Aufträge und keine Wiederherstellung über neue Browser-Sitzungen oder Geräte hinweg. Nach einem erfolgreichen erneuten Start muss die eigentliche Verarbeitung separat ausgelöst werden; der Button bestätigt nur den Jobstatus. Für eine zuverlässige automatische Abarbeitung ist ein Worker-/Queue-Scheduler nötig.
