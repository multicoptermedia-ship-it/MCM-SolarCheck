# Nächster Integrationsblock – Bestandsdienste statt Neuentwicklung

## Vorhanden
- `ProjectCreationService` validiert Projektanlage mit Kunde, Projekt-ID, Name und kWp.
- `ProjectUploadService` validiert Typ, Dateinamen, Signatur, Größe und Eigentümerschaft.
- `ProjectProcessingService` bindet die Verarbeitung an autoritative Compute-Jobs.
- `build_offline_services` verwendet die bestehende lokale SQLite-Projektdatenbank.
- `build_online_verification_server` integriert Registrierung und projektbezogene Dienste.

## Integrationsreihenfolge
1. Projektlisten-Adapter mit realen ProjectApplicationService-Datentypen abgleichen und testen.
2. Offline-Lokalserver mit bestehender Offline-Komposition verbinden, ohne zweite Datenbank anzulegen.
3. Online-HTTP-Routen unter bestehender Session-, Verifizierungs- und Ownership-Prüfung integrieren.
4. Uploads über den vorhandenen ProjectUploadService; keine direkte Ablage aus dem Browser.
5. Compute-Jobs/Review/Befunde serverseitig zugeordnet bereitstellen und Export separat autorisieren.

## Sicherheit
Keine Online-Demo-Freischaltung durch `mode=offline` aus dem Browser. Der Offline-Modus wird ausschließlich vom lokalen, loopback-gebundenen Prozess gewählt. Online-Demo- und Zahlungsberechtigungen bleiben serverseitig. Die gemeinsame UI darf keine fingierten Hotspots anzeigen.

## Status
Dies ist ein Integrationsvertrag und Arbeitsplan; noch keine vollständig verdrahtete End-to-End-Pipeline.

## Priorität 22.10.2026 – konkreter Offline-Projektimport verbunden

Die alte Anweisung, einen neuen Projektlisten-Adapter zu erstellen,
ist nur noch historischer Kontext: `ProjectApplicationService`
verwaltet persistierte Offline-Projekte bereits. Der echte
Lückenschluss in dieser Etappe ist die direkte Bedienfolge
**bestehendes Projekt → zwei private Original-ZIPs → geprüfte
Paarbildung → dauerhafte lokale Originalkopien → atomare SQLite-
Bildspeicherung → echte Projektübersicht**. Die GUI verwendet
den vorhandenen Import-QThread, nicht eine zweite Datenbank.

Die Fortschrittsanzeige misst Prüf- und Kopierschritte, nicht
eine fachlich abgeschlossene PV-Anlagenanalyse. Kein automatischer
KI-Trainingsaufruf oder Bericht. Nächster End-to-End-Praxistest
auf Windows 10 und danach die Phasen A–F aus
`docs/MASTER_PLAN.md`. Online-HTTP-/Payment-Integrationen
dürfen diese lokale Abnahme nicht überspringen.

## Vorrangige Importentscheidung 22.10.2026 – Originaldateien statt ZIP-Pflicht

Der normale Anwender importiert **unverpackte DJI-M3T-Originaldateien** direkt
über **„DJI-Originaldateien auswählen (ohne ZIP)“** oder verwendet den bisherigen
**Bildordnerimport**. Vorherige Dokumentationsformulierungen, die ZIP als
Regelfall erscheinen lassen, sind historische Test-/Transferbeschreibung.
Die privaten ZIPs entstanden für den komprimierten Datentransfer an die
Entwicklung und sind **kein Produktzwang**.

Die neue Mehrfachdateiauswahl übergibt genau die gewählten Originale an den
vorhandenen QThread, validiert DJI-Dateiname, Sensorformat, EXIF-Kamera und
Aufnahmezeit sowie doppelte Identitäten, erstellt unveränderte private Kopien
mit SHA-256-Provenienz und benutzt dann **denselben atomaren
`ProjectApplicationService.import_project_images_cancellable`** zum
Speichern. Ohne vorherige ZIP-Erstellung und ohne zweite Projektdatenbank.
Ausdrücklich angewählte reine Thermaldateien werden mitgenommen und
nicht in scheinbare RGB/Thermal-Paare umgerechnet. Fehlende Paare
bleiben ersichtlich; Bildzähler-Zuordnung ist noch keine
pixelgenaue Registrierung. Dateikopie/Fehler/Abbruch vor SQLite-Commit
hinterlassen keine neue fachliche Projektpersistenz. Der etablierte
Ordnerimport wird nicht deaktiviert; sein Verhalten wurde in diesem
Block nicht stillschweigend umgeschrieben.

Die ZIP-Auswahl existiert nur noch als **optionale Sonderfunktion** für
bereits archivierte/übertragene Originale. Der ältere
Windows-10-Original-**ZIP**-Vor-/Nachprüfer ist entsprechend **nur**
für diese Sonderprüfung gedacht; er ist kein notwendiger Schritt
beim normalen Dateien- oder Ordnerimport.

**Abnahme noch ausstehend:** Das reale Windows-10-Gerät mit 160 originalen
Thermaldateien + 33 RGB-Dateien, reale EXIF-/MPO-Kompatibilität,
persistierte Mengen/Quellreferenzen, Abbruchfall, GUI-Neustart und
Bedienprüfung. Keine Aussage zu kalibrierten °C, physischer Modul-ID,
kundentauglichem Bericht, KI-Training oder allgemeiner Freigabe.

