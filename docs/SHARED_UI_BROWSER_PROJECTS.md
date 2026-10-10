# Offline-Projektliste im Browser

Start aus dem Repository-Wurzelverzeichnis: `python -m offline.preview --port 8765` (Python-Umgebung mit installierten Projektabhängigkeiten und `src` auf dem Importpfad). Optional: `--database /pfad/solarcheck.sqlite3`.

Der Loopback-Server liefert `GET /api/projects` aus der bestehenden Offline-SQLite-Datenbank. Die gemeinsame `frontend/index.html` zeigt reale Projektnamen und IDs als Text; fehlende Daten bleiben als Fehler sichtbar. Der Online-Vorschauserver liefert für diese Route 403, bis eine authentifizierte kundengebundene Implementierung existiert. Import, Analyse und Bericht sind noch deaktiviert.

**Sicherheit:** Diese Vorschau bindet ausschließlich an `127.0.0.1`. Sie ist nicht für Veröffentlichung oder fremde Benutzer vorgesehen. Kein Zahlungs- oder Demo-Gate wird hier ersetzt.
