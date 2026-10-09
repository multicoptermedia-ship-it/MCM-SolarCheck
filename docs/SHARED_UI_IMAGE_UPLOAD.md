# Gemeinsame Oberfläche: Online-Bilddatei-Upload

In der gemeinsamen Oberfläche können angemeldete und freigeschaltete Online-Kunden ein eigenes Projekt auswählen und eine RGB-/Thermalbilddatei über den **bereits vorhandenen** Endpunkt `POST /project-upload` übertragen. Projekt- und Dateiname stehen in `X-SolarCheck-Project-Id` und `X-SolarCheck-Filename`; der Dateiinhalt ist der Request-Body. Der bestehende Online-Server prüft Session, Kundenzugang, Projektzuordnung und die serverseitige Upload-Grenze (250 MiB). Die Browserprüfung ist nur zusätzliche Bedienhilfe.

Nach HTTP-Erfolg zeigt die Oberfläche lediglich eine Upload-Bestätigung: **kein Analyseergebnis und keine erfundenen Befunde**. Verarbeitung, Job-Verwaltung und Ergebnisanzeige folgen separat. Offline bleibt der Upload-Button ausgeblendet, bis ein eigener lokaler, geschützter Importpfad über den vorhandenen Projektservice verfügbar ist. Demo-, Berichts-, Export- und Zahlungsregeln bleiben unverändert.
