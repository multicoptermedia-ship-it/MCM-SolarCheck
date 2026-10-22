# DJI Mavic 3 Thermal – private Original-ZIP-Inventur: 160 T und 33 RGB

## Ausgangslage vom 21. Oktober 2026

Nutzer hat zwei eigene Originalarchive einer etwa 600-kWp-Photovoltaikanlage
in diesem Gespräch bereitgestellt: `Thermal1.zip` und `RGB1.zip`.
Diese **privaten Originaldaten gehören niemals in das Git-Repository, ein
GitHub-Issue, CI-Artefakte oder Online-KI-Training**. Die Auswertung erfolgt
auf dem lokalen Rechner. Die Beispiele hier zeigen keine GPS-Positionen,
Kundennamen oder Originalbildpixel.

Ergebnisse einer ersten read-only Untersuchung der bereitgestellten ZIPs:

| Prüfung | Wert |
|---|---|
| Thermalbilder | **160** (`_T.JPG`) |
| RGB-Bilder | **33** (`_V.JPG`) |
| Bildzähler | Thermal **0128–0287**, RGB **0128–0160** |
| Gemeinsam vorhandene Zähler | **33** |
| RGB ohne passenden Thermalcounter | **0** |
| Thermal ohne RGB | **127** |
| Bildzeitstempel der 33 Paare | Im Originaldateinamen übereinstimmend |
| Kameramodell laut EXIF | **DJI M3T** in allen 193 Bildern |
| Thermisches Hauptbild | **640 × 512** |
| RGB-Hauptbild | **4000 × 3000** |
| Dateicontainer | DJI JPEG/MPO; je **zwei** enthaltene Bildansichten |
| Thermal APP3-/APP4-/APP5-Struktur | In allen **160** untersuchten Thermaldateien erwartete Blockgrößen |
| Temperaturumrechnung in °C | **Nicht validiert** |
| Expertenbestätigte PV-Fehlerlabels | **Nicht vorhanden** |
| Zusätzliche Trainingsrechte | **Nicht automatisch erteilt** |

Diese Befunde sind eine technische, rein lokale **Bestandsprüfung**,
keine fachliche Aussage über den Zustand der Anlage oder die
Rechte für KI-Training. Die zusätzliche MPO-Bildansicht ist ein
anderer Bildinhalt als die 16-Bit-APP3-Rohpixel; sie wird nicht
stillschweigend als radiometrische Temperaturkarte interpretiert.

## Neue sichere Programmbausteine

- `importers/m3t_original_archive_audit.py`: prüft Eingabe-ZIPs,
  absolute Quellpfade, Doppelnummern, Pfadtraversal, Eintragsformate,
  EXIF-Kameramodell, Originalbildgröße und das Aufnahmedatum.
  Eine gültige Zuordnung verlangt **Nummer UND identische
  14-stellige Aufnahmezeit**; nur die Bildnummer allein reicht nicht.
  Das Ergebnis enthält für die Benutzeroberfläche ausschließlich
  Summenzahlen. Keine GPS-/XMP-/Kunden-/Fotodaten werden protokolliert.
- `importers/m3t_original_zip_staging.py`: legt bei ausdrücklichem
  Wunsch einen **neuen** lokalen Zielordner an, kopiert die
  bestätigten Originaldateien unverändert hinein und dokumentiert
  je Datei SHA-256 und `human_reviewed=false` sowie
  `training_rights_approved=false` im **privaten** Index.
  Ungepaarte Thermalaufnahmen bleiben standardmäßig draußen,
  werden aber vollständig als noch nicht gepaart ausgewiesen.
  Mit ausdrücklichem Schalter können sie für reine
  Thermaldiagnostik zusätzlich kopiert werden.
- `offline/m3t_original_zips.py`: ausschließlich manuell aufgerufene
  lokale CLI, die einen aggregierten Auditbericht erzeugt und
  optional die vorhandene `M3TRadiometricParser`-APP3-Struktur der
  Thermalbilder prüft. Rohdatenprüfung liefert **keine
  physikalisch kalibrierten °C**.
- `tests/test_m3t_original_zip_archive.py` und
  `tests/test_m3t_original_zip_cli.py`: synthetische
  Originalgrößen mit künstlichen EXIF-Werten, keine privaten
  Originalfotos im Repository. Tests gegen Doppelnummern,
  Zeitkonflikt, fehlende Gegenstücke, falsche Sensorgröße,
  Dateimanipulation/Überschreiben und unfreiwillige
  Aufnahme ungepaarter Thermaldateien.

## Anwendung auf dem privaten Windows-10-Rechner

Zunächst im Projektverzeichnis die bereits bereitgestellte Python-`.venv`
verwenden. **Keine Downloads oder Installation erforderlich**:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.m3t_original_zips --thermal-zip "D:\Private-M3T\Thermal1.zip" --rgb-zip "D:\Private-M3T\RGB1.zip" --verify-raw-app3 --report "D:\Private-M3T\m3t-audit-aggregate.json"
```

Nur zur Prüfung ist **keine Extraktion** notwendig. Die
`--verify-raw-app3`-Option kontrolliert die APP3-Rohdatenstruktur
aller 160 Thermalbilder, nicht Celsius-Kalibrierung und nicht die
fachliche Bedeutung einzelner Anomalien. Der Bericht wird nur in
einem **neuen, noch nicht existierenden** Dateipfad geschrieben.

Optional kann man **nur die 33 sicher gepaarten Bilder** lokal in
einen bislang nicht vorhandenen Zielordner kopieren:

```powershell
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.m3t_original_zips --thermal-zip "D:\Private-M3T\Thermal1.zip" --rgb-zip "D:\Private-M3T\RGB1.zip" --stage-new-folder "D:\Private-M3T\MCM-Paare-33"
```

Für eine **bewusste gemeinsame Ablage aller 160 Thermalbilder plus
der 33 passenden RGB-Bilder** ausdrücklich
`--include-unpaired-thermal` zusätzlich zu
`--stage-new-folder "D:\Private-M3T\MCM-Alle-193"` setzen.
Die übrigen **127 Thermalbilder bleiben dabei ungepaart** und
dürfen nicht als 160 validierte Bildpaare angegeben werden.

Die Original-ZIPs und ihre Bildbytes werden nicht verändert.
Bestehende Ziele und dortige Daten werden niemals überschrieben.
Kundenprojekte, Berichtfreigaben, Admin-Passwörter,
SolarCheck-Online-Konten und Trainingsledger bleiben unangetastet.
Der optionale Arbeitsordner enthält weiterhin EXIF inklusive GPS:
**nicht öffentlich teilen**, keine automatischen Trainingsuploads.

## Weitere fachliche Schritte

1. Einlesen der bereitgestellten Originalkopien über den bestehenden
   `M3TImporter` und `M3TRGBImporter` in ein **explizit neu
   angelegtes lokales Testprojekt**, nach Prüfung der lokalen
   Datenrechte. Keine unbemerkten Änderungen an echten Kundenprojekten.
2. Technische Qualitätsprüfung der extrahierten Rohwerte; die
   APP3-Struktur allein liefert **noch keine in Grad Celsius
   kalibrierten Temperaturen**. DJI-Verfahren oder unabhängige
   Messreferenzen sind zwingend erforderlich.
3. Auswahl fachlich aussagekräftiger Paare, unabhängige menschliche
   Feststellung möglicher Fehler und gesonderte Nutzungsfreigabe für
   das KI-Training. Ohne diese Rechte bleibt alles im lokalen
   Prüfbereich.
4. Bildgeometrie und RGB/Thermal-Feldsicht werden **nicht**
   allein aus der gleichen Bildnummer als deckungsgleich angenommen.
   Für die Überlagerung gelten weiter die vorhandenen
   Registrierungs-/Kontrollpunktprüfungen.
5. Modellqualität ist anhand weiterer Anlagen getrennt zu validieren,
   da diese 193 Dateien aus derselben Anlage stammen.

**Windows-10-Abnahme:** Die kontinuierliche Win32-CI läuft auf
Windows Server 2022, nicht auf deinem echten Windows-10-Rechner.
Die hier genannten Originaldatei-Analysen stammen aus einer
privaten Sitzung; die Originaldaten wurden **nicht** auf GitHub-CI
hochgeladen. Die CI verwendet nur synthetische Bilder.

## 22.10.2026 – Original-ZIP-Import jetzt direkt im Offline-Programm

Die vorherigen manuellen CLI-Prüfungen bleiben verfügbar, sind aber
für die normale erste Projekterfassung nicht mehr der einzige Weg.
Im **Offline-SolarCheck**:

1. Ein **neues leeres Projekt** anlegen und öffnen.
2. **Import → „DJI-Original-ZIPs (Thermal + RGB) auswählen“**.
3. Private originale Thermal-ZIP und passende RGB-ZIP auswählen.
4. Die Checkbox für zusätzliche **ungepaarte Thermalbilder** bleibt
   standardmäßig aus. Auf Wunsch bewusst einschalten, damit außer
   den 33 Bildpaaren auch die weiteren 127 Thermalaufnahmen
   importiert werden. Nicht als 160 Bildpaare interpretieren.
5. Der Import prüft Dateiformat, DJI-M3T-Kamera, Größe,
   Doppelnummern und Zeitstempel, legt sichere lokale Kopien in
   `private-m3t-originals/<zufaelliger-name>` neben der
   Offline-SQLite-Datenbank ab und importiert Bildmetadaten,
   erkennbare thermische Kandidaten und Paare über die
   bestehende atomare SQLite-Grenze.
6. Der Bereich **Import** zeigt anschließend nur tatsächlich
   persistierte Bildzahlen. Bilder bleiben lokal; Review,
   validierte Temperaturen, fachliche Fehlerfreigabe und
   KI-Trainingsfreigabe erfolgen **nicht automatisch**.

Ein bereits mit Bildern gefülltes Projekt weist einen erneuten
automatischen ZIP-Gesamtimport ab. Das schützt vor Vermischung
zweier Datensätze und unbeabsichtigter Änderung bereits
geprüfter Befunde. Bei einem fehlgeschlagenen Import werden
neue Kopien entfernt; Original-ZIPs bleiben unverändert.
Ein echter Durchlauf mit den 160 privaten Bildern auf Windows 10
ist noch nicht erfolgt. Synthetische Regressionstests in CI
ersetzen diese lokale Abnahme nicht.
