# Bedienbarer vertikaler Prüfablauf: Bestandsaufnahme

- `shared_ui/server.py` ist ein Loopback-Vorschau-HTTP-Server. Er liefert `/api/runtime` mit `features_ready: false` und Offline-Projektlisten aus SQLite. Eine fachliche Prüf-/Export-API fehlt.
- `infrastructure/verification_http_server.py` liefert die gemeinsame Oberfläche nur nach Online-Session- und Kundenprüfung; dort keine Prüfentscheidung-/Export-Endpunkte.
- `frontend/index.html` ist die gemeinsame HTML-Oberfläche.
- Der vertikale Backendkern enthält Kandidatenanalyse, fachliche Entscheidung, Review-Snapshot, Berichtmodell und DOCX/ODT/PDF-Export. **Ein durchgängiger interaktiver Workflow ist nicht vorhanden.**

## Inkrement
Ein lokaler, isolierter Review-Entwurf mit ausschließlich expliziten Entscheidungen, übersichtlichen Kandidaten und kontrolliertem Export. Kein neues ungeschütztes Online-API; keine Behauptung, dass Live-DJI-Projekte oder automatische Modulzuordnung schon funktionieren.

## Offene Voraussetzungen
Lokale sichere Projektdateiauswahl, Bildvorschau, Persistenz/Versionierung der Review-Entscheidungen, gemessene Modulanzahl und Zuordnung, Authentifizierung für Online-Nutzung, PDF-Freigabe sowie ein echter M3T-E2E-Datensatz.
