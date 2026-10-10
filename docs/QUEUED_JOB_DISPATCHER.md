# Explizite Warteschlangen-Disposition

`QueuedJobDispatcher.dispatch(pending)` erhält vom Aufrufer eine Liste persistierter, kundenbezogener `PendingProjectJob`-Identitäten. Er prüft jeden Auftrag über den autoritativen Jobservice, versucht die atomare Kapazitätszulassung und übergibt ausschließlich `running`-Jobs an `ParallelProjectWorkers`. Bei zwei verfügbaren Plätzen können zwei Kunden parallel verarbeitet werden; der dritte bleibt `queued`. Doppelte Einträge innerhalb eines Aufrufs werden ignoriert.

**Bewusste Grenze:** Noch kein produktiver automatischer Queue-Scanner, kein Polling, kein Neustart-Recovery und keine HTTP-Anbindung. Der aufrufende Dienst muss wartende Jobs dauerhaft auffinden und bei freier Kapazität erneut disponieren. Worker-Leases, Crash-Recovery, echte Persistenz und atomare Zulassung bleiben Anforderungen für den produktiven Einsatz. `dispatch` propagiert Worker-Scheduling-Fehler; ein bereits auf `running` gesetzter Job erfordert dann explizite Wiederherstellung statt stillschweigender Falscherfolgsmeldung.

`main`, Berichtsfreigabe, Zahlung und Befundbewertung bleiben unberührt.
