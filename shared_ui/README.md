# Gemeinsame API-Grenze

Der Präsentationsvertrag unter `contracts.py` unterscheidet Online und Offline, ohne Zugriffsrechte zu vergeben. `project_adapter.py` ist ein bewusst schmaler, nur lesender Adapter: Ein Online-Caller muss vorher einen kundengebundenen, autorisierten Dienst bereitstellen. Direkte HTTP-Endpunkte für Projekte, Uploads, Analysen oder Berichte sind **noch nicht** freigeschaltet.

Die bestehende Online-Logik in `src/mcm_solarcheck/online` und die Offline-Logik in `src/mcm_solarcheck/offline` bleiben die fachlichen Quellen. Keine Datenbank- oder Berechtigungslogik wird in die Oberfläche kopiert.
