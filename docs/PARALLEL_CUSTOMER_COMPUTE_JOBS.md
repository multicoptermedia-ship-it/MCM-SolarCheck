# Parallele Online-Aufträge: zwei Kapazitätsplätze

Die bestehende atomare `ComputeJobService.start(..., capacity=ComputeCapacity(...))`-Zulassung wird in beiden HTTP-Abläufen verwendet: bei Neuanlage und beim erneuten Zulassungsversuch wartender Aufträge. Die Standardkapazität ist jetzt **2**, konfigurierbar über `build_online_verification_server(..., max_parallel_compute_jobs=N)`. Ungültige Kapazitäten (z. B. 0) werden durch `ComputeCapacity` abgewiesen.

**Gewünschtes Verhalten:** Zwei Aufträge, auch von zwei verschiedenen angemeldeten Kunden, dürfen gleichzeitig den Zustand `running` erhalten; ein dritter bleibt bei voller Kapazität `queued`. Projektbesitz und Kundenberechtigungen werden weiterhin serverseitig geprüft. Die echte Persistenzschicht stellt die atomare Zulassung bereit; der HTTP-Test bildet die 2/1-Entscheidung zusätzlich mit einem Test-Doppel nach.

**Wichtige Grenze:** Die Zulassung von zwei Jobs zum Status `running` allein startet noch keine zwei Analyse-Worker. Tatsächlich parallele Bildverarbeitung, automatische Queue-Abarbeitung und eine passende Worker-/Ressourcenbegrenzung müssen gesondert integriert und unter Last geprüft werden. `running` ist deshalb noch kein Nachweis, dass bereits Bildanalyse läuft. Keine fingierten Befunde und keine Änderung an Berichts- oder Zahlungsgates.
