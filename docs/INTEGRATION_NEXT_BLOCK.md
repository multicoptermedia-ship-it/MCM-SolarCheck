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
