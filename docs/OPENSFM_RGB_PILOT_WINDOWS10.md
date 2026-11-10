# Erster lokaler RGB-Orthofoto-Pilot mit OpenSfM

**10.11.2026 · GPU-Funktionstest bestanden:** Nutzer meldet status passed, MX250/2047 MiB und64 korrekt zugeordnete künstliche Deskriptoren im OpenSfM-eigenen Matcher. NVIDIA582.78 und getrennte Import-/Native-Zeitfenster sind bestätigt. Compiler, Umgebung, Quellbau und GPU-Startprüfung sind abgeschlossen; nichts davon erneut installieren oder prüfen. Dataset und Dense waren ausdrücklich not_tested.

**OPEN-SFM-RGB-01** verbindet nun die vorhandene Projektwahl/den nur lesenden RGB-Projektzugriff und geprüfte Arbeitskopien mit den installierten Standardstufen von OpenSfM. Kein neuer Importer und keine neue Photogrammetrie-Engine. Dies ist ein separater lokaler Pilot; das Hauptprogramm und seine vorhandenen Projekte werden nicht aktualisiert oder umregistriert. Der tatsächliche Windows-10-/Bildqualitätslauf bleibt offen.

## Bedienung

1. Den unten bereitgestellten Startblock einmal ausführen. Er soll ausschließlich die gepinnte SolarCheck-Quell-ZIP nach E: entpacken und den Dialog mit dem bereits vorhandenen Python **F:\MCM-SolarCheck\.venv\Scripts\python.exe** starten. Keine Paketinstallation oder neuer OpenSfM-Build. OpenSfM selbst läuft weiterhin in **E:\SolarCheck-OpenSfM\env** über das vorhandene Miniforge.
2. Im Dialog die **vorhandene Projektdatei** und danach ausdrücklich das richtige Projekt wählen. Die Datenbank wird nur lesend geöffnet. Beide Werkzeugpfade sind mit den bereits bestätigten E:-Pfaden vorbelegt.
3. Für den ersten Lauf ein **kleines vollständiges, zusammenhängend beflogenes RGB-Projekt** wählen. Alle bereits importierten RGB-JPGs dieses Projekts werden verarbeitet, ohne die ersten N Bilder stillschweigend auszuwählen. Grenze:3 bis300 RGB-Bilder. Thermalbilder werden nicht an diesen RGB-Job gegeben. Kein erneuter Import oder Upload nötig.
4. Einen privaten Ausgabeordner getrennt von Originalen und Git wählen, etwa den bereits verwendeten F:\Auswertung1. **RGB-Pilot starten** anklicken. Ein frischer opensfm-rgb-…-Ordner wird angelegt; Originaldateien und Datenbank bleiben erhalten.
5. Der Dialog zeigt Stufe und verstrichene Gesamtlaufzeit. Höchstens60 Minuten je Stufe, drei Stunden insgesamt. Bei Abbruch/Schließen wird nur der eigene Prozessbaum beendet; Arbeitsdateien und Protokolle bleiben erhalten. **Ausgabeordner öffnen** funktioniert auch bei einem Fehler, sobald der Jobordner angelegt wurde. Nicht erneut starten, bevor der erste Befund geprüft ist.

## Standardstufen und Ergebnis

OpenSfM führt Metadaten → Merkmale → Bildabgleich → Tracks → Rekonstruktion → Entzerrung → dense_clustering → compute_depthmaps → fuse_depthmaps → dense_merging --georeferenced aus. Der Adapter delegiert an den regulären Upstream-command_runner und den DataSet-Kontext mit clean_up; keine kopierten Algorithmen und kein unvollständiges run_all.bat.

Nach der normalen Metadatenstufe werden nur deren erzeugte Positionsdaten auf Vollständigkeit geprüft, keine separate Original-EXIF-Inventur. Es werden keine GPS-/RTK-Werte, Kameramodelle oder Linsenkalibrierungen erfunden/überschrieben. Externe Selbstkalibrierung erfolgt ausschließlich in OpenSfM. Die JPEG-Arbeitskopien behalten EXIF/XMP; Metadaten der ursprünglichen Dateien werden nicht geändert.

**Vor Dense muss genau ein vollständiger Kameraverbund alle ausgewählten RGB-Aufnahmen enthalten.** Teilmodelle werden nicht zusammengebaut oder als größtes Modell weitergegeben. Fehlende/fremde Aufnahmen, ungültige Kameraposen oder leere/ungültige Punkte stoppen den Job. Diese technische Mindestbedingung beweist noch keine richtige Dachgeometrie.

Der Pilot verwendet vorhandene OpenSfM-Konfigurationsparameter: vier CPU-Prozesse, HAHOG2048 und OPENCL_BF, GPS-/Zeit-/Reihenfolgen-Nachbarn statt unbeschränktem Allpaar-Abgleich; Dense maximal1600 Pixel lange Seite/vier Matchingansichten/kleinere Cluster. Die übliche CPU-Fallback-Umschaltung bei fehlender GPU wird vor dem Matching abgelehnt. Das ist ein begrenztes erstes Profil für die2-GiB-MX250, **keine Speicher-/Geschwindigkeitsgarantie oder endgültige PV-Auflösung**. Originale bleiben in voller Auflösung erhalten. Fehler/Timeout ist kein Anlass zu einer blinden Parameter- oder Nachtlaufserie.

Projiziertes RGB-GeoTIFF wird ausschließlich von OpenSfM erzeugt: **undistorted\depthmaps\ortho.tif**. Ohne eigene GCP-Vorgabe wählt das Werkzeug die passende UTM-Zone aus seiner Referenzlage. Der vorhandene GeoTIFF-Inspektor prüft eingebettetes CRS/Transform; zusätzlich projiziertes RGB/RGBA und nichtleere Datenmaske. Es wird kein fehlendes CRS nachträglich eingesetzt, kein Raster selbst gerendert und keine Qualität freigegeben.

Nach Erfolg das TIFF lokal ansehen; später den vorhandenen GeoTIFF-Import und die Anlagenübersicht verwenden. Noch keine automatische Projektregistrierung: Das passende Thermal-Orthofoto fehlt für die atomare Paarübernahme. Dach-/PV-Abdeckung, scharfe Modulränder, Nähte, Lage und Laufzeit müssen real geprüft werden. Auch ein fertiges RGB allein erfüllt den Auftrag mit beiden Orthofotos nicht.

## Nur diese Kennzahlen zurückgeben

**laufzeiten.json** im neuen Jobordner enthält Status, Bild-/Kamera-/Modell-/Punktzahlen und Stufenlaufzeiten. Diese Datei beziehungsweise ihr Text kann als nächster Befund übermittelt werden. Keine Bildnamen, Originalpfade oder Kamerakoordinaten darin. georeferencing_verified, temperature_verified und thermal_created bleiben false.

job.json, input-map.json, Metadaten, Rekonstruktionen, TIFFs und step-XX.log sind **private lokale Daten**. Sie bleiben auf dem Auswerterechner; nicht vollständig hochladen oder nach Git kopieren. Fehlerdialog nennt nur Stufe, Exitcode beziehungsweise Zeitlimit und relativen Lognamen. Wiederöffnung/Sichtprüfung erfolgt aus dem erhaltenen Ordner ohne erneute Berechnung.

## Startblock

Wird nach Windows-Abnahme mit fester Quellversion und SHA256 der Quell-ZIP ergänzt. Bis dahin keinen neuen Bildlauf starten. Die bestehenden GPU-/Buildprüfungen sind abgeschlossen.

## Prüfstand

Lokal29 Tests bestanden, zwei native Tk-Fälle auf Linux ohne Display übersprungen. Synthetische Tests verbinden alle zehn Stufen, Eingabeunveränderlichkeit, Teilmodell-Stopp, GPS-/Raster-Grenzen, Abbruch-/Zeitlimitstatus und sichere Kennzahlen. Ein tatsächlicher isolierter Pythonprozess prüft die dünne CLI-Delegation/cleanup gegen eine bewusst funktionslose Test-Engine; dies ist kein echter OpenSfM-/Bildtest. Windows-Prozess-/Tk-Abnahme noch offen. Kein Kundenbild wurde hier verarbeitet.

Der gemeinsame Jobkern akzeptiert RGB-Datensätze und einen expliziten Engineaufruf; Datenbankwahl, Windows-Pfade und Tk bleiben im Desktopadapter. Für die spätere Onlinefassung ist derselbe Jobkern verwendbar. Jetzt keine zweite Web-/Cloudkette oder neue Engine, keine ODM/WebODM/ODX-Integration und kein Merge nach main. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).
