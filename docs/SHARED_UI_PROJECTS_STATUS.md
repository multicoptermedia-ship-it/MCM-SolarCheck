# Gemeinsame Projektübersicht – Status

Der Adapter liest die tatsächlichen Attribute `ProjectRecord.project_id` und `ProjectRecord.name` aus `ProjectApplicationService.projects()`. Der Offline-Leseweg nutzt `build_offline_services` und damit die bestehende SQLite-Datenbank. Eine neue Datenbank oder parallele Projektverwaltung wird nicht angelegt.

**Wichtig:** Der Offline-Adapter ist derzeit eine Python-Schnittstelle, noch kein Browser-HTTP-Endpunkt. Der Online-Modus darf niemals den unbeschränkten `projects()`-Aufruf verwenden; er muss die vorhandene kundengebundene `projects_for_customer(customer_id)`-Grenze und Sessionprüfung benutzen. Analyse und Berichte sind weiterhin nicht an die Vorschau angeschlossen.
