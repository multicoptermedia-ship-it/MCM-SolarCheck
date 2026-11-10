# Erster lokaler RGB-Orthofoto-Pilot mit OpenSfM

**Aktueller Nutzerbefund 10.11.2026:** 287/287 RGB-Aufnahmen in einem Modell, 137082 Punkte. Tiefenkartenstufe nach einer Stunde begrenzt beendet, Gesamt rund1 h45 min; noch kein Orthofoto. Vorhandenen Lauf nachlesen, nicht neu starten. Die zuvor übermittelten COLMAP-Berichte stammen von anderen Jobs.

**10.11.2026 · GPU-Funktionstest bestanden:** Nutzer meldet status passed, MX250/2047 MiB und64 korrekt zugeordnete künstliche Deskriptoren im OpenSfM-eigenen Matcher. NVIDIA582.78 und getrennte Import-/Native-Zeitfenster sind bestätigt. Compiler, Umgebung, Quellbau und GPU-Startprüfung sind abgeschlossen; nichts davon erneut installieren oder prüfen. Dataset und Dense waren ausdrücklich not_tested.

**OPEN-SFM-RGB-01** verbindet nun die vorhandene Projektwahl/den nur lesenden RGB-Projektzugriff und geprüfte Arbeitskopien mit den installierten Standardstufen von OpenSfM. Kein neuer Importer und keine neue Photogrammetrie-Engine. Dies ist ein separater lokaler Pilot; das Hauptprogramm und seine vorhandenen Projekte werden nicht aktualisiert oder umregistriert. Der Windows-10-Nutzerlauf hat den vollständigen Kameraverbund erreicht; Dense-Abschluss und Bildqualität bleiben offen.

## Bedienung für einen späteren neuen Bildlauf

**Jetzt zuerst nur den vorhandenen Lauf laden**, wie unten beschrieben. Die folgenden Schritte starten eine neue Verarbeitung und sind für das Nachlesen nicht nötig.

1. Den unten bereitgestellten Startblock einmal ausführen. Er soll ausschließlich die gepinnte SolarCheck-Quell-ZIP nach E: entpacken und den Dialog mit dem bereits vorhandenen Python **F:\MCM-SolarCheck\.venv\Scripts\python.exe** starten. Keine Paketinstallation oder neuer OpenSfM-Build. OpenSfM selbst läuft weiterhin in **E:\SolarCheck-OpenSfM\env** über das vorhandene Miniforge.
2. Im Dialog die **vorhandene Projektdatei** und danach ausdrücklich das richtige Projekt wählen. Die Datenbank wird nur lesend geöffnet. Beide Werkzeugpfade sind mit den bereits bestätigten E:-Pfaden vorbelegt.
3. Für den ersten Lauf ein **kleines vollständiges, zusammenhängend beflogenes RGB-Projekt** wählen. Alle bereits importierten RGB-JPGs dieses Projekts werden verarbeitet, ohne die ersten N Bilder stillschweigend auszuwählen. Grenze:3 bis300 RGB-Bilder. Thermalbilder werden nicht an diesen RGB-Job gegeben. Kein erneuter Import oder Upload nötig.
4. Einen privaten Ausgabeordner getrennt von Originalen und Git wählen, etwa den bereits verwendeten F:\Auswertung1. **RGB-Pilot starten** anklicken. Ein frischer datums-/uhrzeitführender OpenSfM_RGB-Projektordner wird angelegt; Originaldateien und Datenbank bleiben erhalten.
5. Der Dialog zeigt Stufe und verstrichene Gesamtlaufzeit. Höchstens60 Minuten je Stufe, drei Stunden insgesamt. Bei Abbruch/Schließen wird nur der eigene Prozessbaum beendet; Arbeitsdateien und Protokolle bleiben erhalten. **Ausgabeordner öffnen** funktioniert auch bei einem Fehler, sobald der Jobordner angelegt wurde. Nicht erneut starten, bevor der erste Befund geprüft ist.

## Standardstufen und Ergebnis

OpenSfM führt Metadaten → Merkmale → Bildabgleich → Tracks → Rekonstruktion → Entzerrung → dense_clustering → compute_depthmaps → fuse_depthmaps → dense_merging --georeferenced aus. Der Adapter delegiert an den regulären Upstream-command_runner und den DataSet-Kontext mit clean_up; keine kopierten Algorithmen und kein unvollständiges run_all.bat.

Nach der normalen Metadatenstufe werden nur deren erzeugte Positionsdaten auf Vollständigkeit geprüft, keine separate Original-EXIF-Inventur. Es werden keine GPS-/RTK-Werte, Kameramodelle oder Linsenkalibrierungen erfunden/überschrieben. Externe Selbstkalibrierung erfolgt ausschließlich in OpenSfM. Die JPEG-Arbeitskopien behalten EXIF/XMP; Metadaten der ursprünglichen Dateien werden nicht geändert.

**Vor Dense muss genau ein vollständiger Kameraverbund alle ausgewählten RGB-Aufnahmen enthalten.** Teilmodelle werden nicht zusammengebaut oder als größtes Modell weitergegeben. Fehlende/fremde Aufnahmen, ungültige Kameraposen oder leere/ungültige Punkte stoppen den Job. Diese technische Mindestbedingung beweist noch keine richtige Dachgeometrie.

Der Pilot verwendet vorhandene OpenSfM-Konfigurationsparameter: vier CPU-Prozesse, HAHOG2048 und OPENCL_BF, GPS-/Zeit-/Reihenfolgen-Nachbarn statt unbeschränktem Allpaar-Abgleich; Dense maximal1600 Pixel lange Seite/vier Matchingansichten/kleinere Cluster. Die übliche CPU-Fallback-Umschaltung bei fehlender GPU wird vor dem Matching abgelehnt. Das ist ein begrenztes erstes Profil für die2-GiB-MX250, **keine Speicher-/Geschwindigkeitsgarantie oder endgültige PV-Auflösung**. Originale bleiben in voller Auflösung erhalten. Fehler/Timeout ist kein Anlass zu einer blinden Parameter- oder Nachtlaufserie.

Projiziertes RGB-GeoTIFF wird ausschließlich von OpenSfM erzeugt: **undistorted\depthmaps\ortho.tif**. Ohne eigene GCP-Vorgabe wählt das Werkzeug die passende UTM-Zone aus seiner Referenzlage. Der vorhandene GeoTIFF-Inspektor prüft eingebettetes CRS/Transform; zusätzlich projiziertes RGB/RGBA und nichtleere Datenmaske. Es wird kein fehlendes CRS nachträglich eingesetzt, kein Raster selbst gerendert und keine Qualität freigegeben.

Nach Erfolg das TIFF lokal ansehen; später den vorhandenen GeoTIFF-Import und die Anlagenübersicht verwenden. Noch keine automatische Projektregistrierung: Das passende Thermal-Orthofoto fehlt für die atomare Paarübernahme. Dach-/PV-Abdeckung, scharfe Modulränder, Nähte, Lage und Laufzeit müssen real geprüft werden. Auch ein fertiges RGB allein erfüllt den Auftrag mit beiden Orthofotos nicht.

## Nur diese Kennzahlen zurückgeben

**OpenSfM_RGB_…_Kennzahlen.json** im neuen Jobordner enthält Status, Bild-/Kamera-/Modell-/Punktzahlen und Stufenlaufzeiten. Diese Datei beziehungsweise ihr Text kann als nächster Befund übermittelt werden. Keine Bildnamen, Originalpfade oder Kamerakoordinaten darin. georeferencing_verified, temperature_verified und thermal_created bleiben false.

job.json, input-map.json, Metadaten, Rekonstruktionen, TIFFs und step-XX.log sind **private lokale Daten**. Sie bleiben auf dem Auswerterechner; nicht vollständig hochladen oder nach Git kopieren. Fehlerdialog nennt nur Stufe, Exitcode beziehungsweise Zeitlimit und relativen Lognamen. Wiederöffnung/Sichtprüfung erfolgt aus dem erhaltenen Ordner ohne erneute Berechnung.

## Lauf erkennen und vorhandene Kennzahlen kopieren

Neue Ordner beginnen mit der lokalen Verarbeitungszeit, zum Beispiel **20261110_204300_OpenSfM_RGB_Demo-Dach_abcdefgh**. Das Projektkürzel bleibt lokal. Der neue Bericht heißt **OpenSfM_RGB_20261110_204300_abcdefgh_Kennzahlen.json**; pipeline/run_id/started_at unterscheiden Engine und Lauf ohne Kundennamen im teilbaren JSON.

Im Dialog stehen Projekt, Zeit und Laufordner separat zur gewählten Projektdatei. **Kennzahlen kopieren** bezieht sich genau auf den angezeigten abgeschlossenen Lauf und erhält die Fehlermeldung sichtbar. **Lauf laden** öffnet einen vorhandenen OpenSfM-Job ohne neue Bildverarbeitung. Bei alten Jobs fehlt der Projektname im gespeicherten Manifest; die Anzeige bezeichnet die Dateizeit deshalb ausdrücklich als Berichtsstand. Ein COLMAP-Ordner wird abgelehnt.

Für den bereits abgebrochenen Lauf: im bisherigen Dialog **Ausgabeordner öffnen** anklicken und dessen exakten Ordnerpfad merken. Im aktualisierten Dialog **Lauf laden**, diesen Ordner auswählen, dann **Kennzahlen kopieren** und hier als Text einfügen. **RGB-Pilot starten ist dafür nicht erforderlich.** Die vorhandenen Ordner werden nicht umbenannt.

Die Kennzahlen ergänzen stored_depthmaps.raw/clean aus den vorhandenen Engine-Ausgabedateien. Nur Dateianzahlen, kein Bildinhalt und keine Integritäts-/Qualitätsfreigabe. Die Dateiendung .npz bedeutet im geprüften Enginezweig LZ4-verpackte Daten; vorhandene Ladefunktionen sind für eine spätere Prüfung maßgeblich. Noch keine automatische Fortsetzung, Zeitverlängerung oder Cachelöschung.

## Aktualisierter Startblock

Diesen Block vollständig in PowerShell ausführen. Er lädt die fest geprüfte SolarCheck-Quellfassung (ca. 2,9 MB), prüft SHA256, entpackt sie in einen neuen Ordner auf E: und öffnet den Dialog. Vorhandenes F:-Python und OpenSfM bleiben erhalten; keine Installation oder automatische Bildverarbeitung.

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$pilotPython = 'F:\MCM-SolarCheck\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pilotPython -PathType Leaf)) {
    throw 'Vorhandenes SolarCheck-Python auf F: nicht gefunden.'
}
$pilotCommit = '8562af152d872a6b9083b05fc860fa23b6e72836'
$pilotSha256 = 'e181eb0b457d7d4e3f90cc7e1ac9908c0dc88b9e0ef13a07863613fce558d8f2'
$pilotDir = Join-Path 'E:\SolarCheck-Pilot' ('rgb-' + [guid]::NewGuid().ToString('N').Substring(0,12))
New-Item -ItemType Directory -Path $pilotDir -ErrorAction Stop | Out-Null
$pilotZip = Join-Path $pilotDir 'source.zip'
$pilotSource = Join-Path $pilotDir 'source'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pilotCommit" -OutFile $pilotZip
if ((Get-FileHash -LiteralPath $pilotZip -Algorithm SHA256).Hash -ne $pilotSha256) {
    throw 'Pruefsumme stimmt nicht. Start abgebrochen.'
}
Expand-Archive -LiteralPath $pilotZip -DestinationPath $pilotSource -ErrorAction Stop
$pilotRoot = Join-Path $pilotSource ('MCM-SolarCheck-' + $pilotCommit)
$pilotScript = Join-Path $pilotRoot 'scripts\MCM_SolarCheck_OPENSFM_RGB_PILOT.py'
if (-not (Test-Path -LiteralPath $pilotScript -PathType Leaf)) {
    throw 'Startdatei im entpackten Quelltext fehlt.'
}
& $pilotPython $pilotScript
if ($LASTEXITCODE -ne 0) { throw 'Pilotdialog mit Fehler beendet.' }
```

Danach **Lauf laden** → den bisherigen OpenSfM-Laufordner unter F:\Auswertung1 auswählen → **Kennzahlen kopieren** → Text im Chat einfügen. Der Dialog lädt dabei nur den gespeicherten Bericht und zählt vorhandene Tiefenkartendateien; keine erneute Berechnung. Alte generische Dateinamen bleiben lesbar. Neue Berichte und Ordner erhalten eindeutige Namen wie oben beschrieben.

## Prüfstand

Quelle **8562af152d872a6b9083b05fc860fa23b6e72836**: alle drei regulären CI-Workflows erfolgreich. [Windows-CI 42893429947](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42893429947) auf Python 3.11 und 3.12 vollständig bestanden, einschließlich nativer Tk-Bedienung für Start/Ergebnis/Abbruch sowie Laden alter Läufe und Kopieren in die Zwischenablage ohne Engineaufruf. Synthetische Jobtests und tatsächliche isolierte CLI-Prozesse mit inaktiver Test-Engine bestanden. Lokal 33 Tests bestanden; vier native Tk-Fälle ohne Display übersprungen und anschließend auf Windows ausgeführt. Quell-ZIP-SHA256 berechnet und fünf Start-/Helper-/Service-Dateien bytegenau verglichen.

Diese Windows-Server-2022-/Test-Engine-Prüfung belegt keine reale Windows-10-Bildqualität. Der tatsächliche Nutzerbericht belegt bereits 287/287 registrierte RGB-Bilder in einem Modell; Dense wurde am Stundenlimit beendet. Lauf-laden/Kopieren auf dem Auswerterechner und gespeicherte Tiefenkartenanzahlen bleiben als nächster Nutzerbefund offen. Der folgende reine Dokumentations-HEAD ist separat zu prüfen. Keine Kundenbilder wurden hier verarbeitet.

Der gemeinsame Jobkern akzeptiert RGB-Datensätze und einen expliziten Engineaufruf; Datenbankwahl, Windows-Pfade und Tk bleiben im Desktopadapter. Für die spätere Onlinefassung ist derselbe Jobkern verwendbar. Jetzt keine zweite Web-/Cloudkette oder neue Engine, keine ODM/WebODM/ODX-Integration und kein Merge nach main. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).
