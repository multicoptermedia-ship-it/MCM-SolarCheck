# Online-JSON-Projektliste

Der vorhandene Online-HTTP-Server stellt nun `GET /api/projects` bereit, sofern Sessiondienst, Kundenzugangsprüfung und Projektservice konfiguriert sind. Er prüft den vorhandenen `solarcheck_session`-Cookie über `_require_customer_user()`, anschließend den bestehenden `customer_entry`-Gate und liest ausschließlich `projects_for_customer(user_id)`. Die Antwort ist `{"projects": [{"id": "…", "name": "…"}]}` mit `Cache-Control: no-store`.

Ohne gültige Sitzung: 401. Bei verweigertem Kundenzugang: 403. Die vorhandene HTML-Route `/projects` bleibt unverändert. Der separate Online-Vorschauserver bleibt absichtlich ohne Projektdaten und ist nicht mit diesem authentifizierten Server gleichzusetzen.

**Noch offen:** Gemeinsames Frontend am authentifizierten Online-Server ausliefern und weitere Funktionen (Import, Analyse, Bericht) anbinden. Keine Änderung an Demo-, Export- oder Zahlungsregeln.
