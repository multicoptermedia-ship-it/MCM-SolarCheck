# Gemeinsame SolarCheck-Oberfläche

`frontend/index.html` ist das erste gemeinsame UI-Grundgerüst für Online und Offline. Es zeigt keine erfundenen Ergebnisse und deaktiviert noch nicht angebundene Aktionen.

Die vorhandenen Komponenten unter `src/mcm_solarcheck/online`, `src/mcm_solarcheck/offline` und `web/customer-site` bleiben erhalten. Die Kunden-Landingpage ist nicht die Analyseoberfläche.

## Noch zu verbinden

- Gemeinsame API für Upload, Analyse, Ergebnisanzeige, Review und Berichte
- Lokaler Offline-Launcher mit Loopback-Bindung
- Online-Authentifizierung, Demo-Kontingente und Exportberechtigungen
- Gleiche UI online und offline ausliefern
- Tests auf beiden Python-Versionen und CI

Die aktuelle Oberfläche ist ein **Grundgerüst**, keine funktionsfähige Produktintegration. Sicherheitsprüfungen erfolgen ausschließlich serverseitig.