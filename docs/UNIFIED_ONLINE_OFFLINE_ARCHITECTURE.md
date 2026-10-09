# Gemeinsame Online-/Offline-Architektur (Entwicklungsgrundlage)

## Bestandsaufnahme
- Der Integrationsbranch enthält bereits `web/customer-site/` und `src/mcm_solarcheck/`.
- Bestehende Funktionen werden nicht ungeprüft verschoben oder überschrieben.
- `main` bleibt bis zu geprüfter Integration unverändert.

## Verbindliche Produktregeln
1. Eine gemeinsame Weboberfläche für Online und Offline. Die Offline-Anwendung öffnet dieselbe UI über einen lokalen Server im Browser; kein zweites PySide6-UI entwickeln.
2. Gemeinsamer Python-Analysekern für Import, RGB/Thermal, Modul- und Hotspoterkennung, Fehlerhinweise, fachliche Prüfung sowie PDF/ODT.
3. Online: verifizierte Konten, drei kostenlose Demo-Analysen mit eigenen Uploads, Ergebnisansicht mit markierten Modulen/Hotspots und vorsichtig formulierten Fehlerhinweisen. Kein Export und kein Bericht in der Demo.
4. Online-Vollversion: Berichte und Export nur nach serverseitig bestätigter Berechtigung/Zahlung.
5. Offline: ausschließlich lokal auf dem Eigentümerrechner, alle Analyse-/Berichts-/Exportfunktionen ohne Nutzerkonten, Bezahlung, Demo-Limit oder Internetzwang.
6. Nach Fertigstellung und Freigabe des Online-Berichts: E-Mail mit auf die zugehörige Auswertung beschränktem Abruflink (72 Stunden). Token sicher zufällig erzeugen, Hash serverseitig speichern, Ablauf und Berechtigung serverseitig prüfen. E-Mail-Versand zuverlässig über einen Job/Outbox abwickeln.
7. Demo-Zähler dauerhaft und atomar beim verbindlichen Analysebeginn aktualisieren; technische Fehlstarts nicht berechnen. Auch parallele Starts müssen das Limit einhalten.
8. Fehlerklassifikationen als KI-Hinweise mit Konfidenz und Prüfstatus ausgeben; keine ungesicherten Diagnosen behaupten.
9. Uploads validieren und begrenzen, Mandanten strikt trennen, Dateizugriffe autorisieren und Aufbewahrungs-/Löschregeln definieren.

## Vorgesehene Komponenten (Ziel, noch nicht vollständig implementiert)
- `web/customer-site/`: vorhandene Kunden-Weboberfläche als Migrationsquelle.
- `frontend/`: gemeinsame, buildbare Web-UI für beide Betriebsarten.
- `src/mcm_solarcheck/`: bestehende Analysefunktionen; später gemeinsame API-Schnittstelle.
- `backend/`: lokale und serverseitige API mit gleichen Analyse-Endpunkten.
- `online/`: ausschließlich Online-Identität, Kontingente, Zahlungen, E-Mail und Berechtigungen.
- `offline/`: lokaler Launcher, lokale Datenspeicherung, Installationspaket.
- `tests/`: gemeinsame Funktions-, Sicherheits- und End-to-End-Tests.

## Umsetzung in kontrollierten Schritten
1. Bestandsaufnahme aller Web-/Analysefunktionen und Abhängigkeiten auf Integrationsbranch.
2. Gemeinsame Oberfläche aus dem vorhandenen Webauftritt extrahieren, ohne bestehende Seiten zu verlieren.
3. Lokale API/Launcher anbinden und Offline-Funktionsgleichheit testen.
4. Online-Upload, Jobstatus, Demo-Ergebnisse und serverseitige Kontingentprüfung implementieren.
5. Berechtigte Vollberichte, Zahlung und fertige Berichte per E-Mail verlinken.
6. Automatisierte Tests, Offline-Installation und kontrollierte Migration in `main`.

## Abnahmekriterien
- Derselbe UI-Build läuft online und offline.
- Dieselben Analysedaten ergeben dieselben Befunde in beiden Modi (bei gleichen Modellversionen).
- Demo zeigt markierte Hotspots und mögliche Fehler, erlaubt aber keinen Bericht-/Dateiexport über UI **oder API**.
- Ein viertes kostenloses Analyseprojekt wird serverseitig abgewiesen.
- Offline kann vollständig ohne Netz und ohne Online-Konto analysieren und Berichte erzeugen.
- E-Mail wird erst nach bestätigter Fertigstellung/Freigabe versendet; Link läuft nach 72 Stunden ab.
