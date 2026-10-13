# Parallele Projektverarbeitung – Worker-Baustein

`ParallelProjectWorkers` führt bereits zugelassene `running`-Aufträge mit höchstens zwei gleichzeitigen Threads aus. Jeder Aufruf prüft vor der Einplanung `job_id`, `customer_id` und `project_id` über den bestehenden autoritativen Jobservice. Verarbeitungsfehler bleiben über das zurückgegebene Future sichtbar. Der bestehende `ProjectProcessingService` übernimmt Import, Statusaufzeichnung und exklusive Worker-Claims.

**Noch keine vollständige Online-Queue:** Der Pool wird bewusst noch nicht automatisch vom HTTP-Endpunkt gestartet. Die verlässliche Kopplung an eine persistente Queue, Lease-Recovery, Worker-Neustarts, sichere automatische Zulassung wartender Jobs und ein Ressourcenlimit über mehrere Serverprozesse hinweg stehen aus. Ein In-Process-Threadpool ist keine dauerhafte Produktionswarteschlange. Worker-Kapazität und Job-Zulassung müssen im späteren Deployment gleich konfiguriert sein.

Keine Änderungen an `main`, Abrechnung, Demo-Limits, Berichten oder Befundinterpretation.
