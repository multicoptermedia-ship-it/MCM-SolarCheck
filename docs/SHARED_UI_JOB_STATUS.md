# Auftragsstatus in der gemeinsamen Oberfläche

Die authentifizierte Online-Route `GET /api/compute-job?project_id=…&job_id=…` fragt den bestehenden `compute_job_service.get(job_id, user_id=…, project_id=…)` ab. Dadurch bleibt die Zuordnung zu Benutzer und Projekt serverseitig maßgeblich. Die Antwort enthält die tatsächlichen Felder `project_id`, `job_id` und `status` (`queued`, `running`, `completed`, `failed`).

Nach der automatischen Auftragserstellung kann der Kunde den Status mit „Auftragsstatus prüfen“ erneut abfragen. Die Anzeige ist **keine** Ergebnis- oder Befundanzeige. Ein wartender Auftrag wird hier nicht automatisch gestartet; eine Worker-/Queue-Integration und Wiederaufnahme nach Neuladen der Seite stehen noch aus. Offline-Analyse und Berichtsexport sind weiterhin separat zu integrieren.
