# Erster lokaler RGB-Orthofoto-Pilot mit OpenSfM

**Aktueller Nutzerbefund10.11.2026:**287/287 RGB-Aufnahmen in einem Modell,137082 Punkte. Tiefenkartenstufe nach einer Stunde begrenzt beendet, Gesamt rund1 h45 min; noch kein Orthofoto. Vorhandenen Lauf nachlesen, nicht neu starten. Die zuvor übermittelten COLMAP-Berichte stammen von anderen Jobs.

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

**OpenSfM_RGB_…_Kennzahlen.json** im neuen Jobordner enthält Status, Bild-/Kamera-/Modell-/Punktzahlen und Stufenlaufzeiten. Diese Datei beziehungsweise ihr Text kann als nächster Befund übermittelt werden. Keine Bildnamen, Originalpfade oder Kamerakoordinaten darin. georeferencing_verified, temperature_verified und thermal_created bleiben false.

job.json, input-map.json, Metadaten, Rekonstruktionen, TIFFs und step-XX.log sind **private lokale Daten**. Sie bleiben auf dem Auswerterechner; nicht vollständig hochladen oder nach Git kopieren. Fehlerdialog nennt nur Stufe, Exitcode beziehungsweise Zeitlimit und relativen Lognamen. Wiederöffnung/Sichtprüfung erfolgt aus dem erhaltenen Ordner ohne erneute Berechnung.

## Lauf erkennen und vorhandene Kennzahlen kopieren

Neue Ordner beginnen mit der lokalen Verarbeitungszeit, zum Beispiel **20261110_204300_OpenSfM_RGB_Demo-Dach_abcdefgh**. Das Projektkürzel bleibt lokal. Der neue Bericht heißt **OpenSfM_RGB_20261110_204300_abcdefgh_Kennzahlen.json**; pipeline/run_id/started_at unterscheiden Engine und Lauf ohne Kundennamen im teilbaren JSON.

Im Dialog stehen Projekt, Zeit und Laufordner separat zur gewählten Projektdatei. **Kennzahlen kopieren** bezieht sich genau auf den angezeigten abgeschlossenen Lauf und erhält die Fehlermeldung sichtbar. **Lauf laden** öffnet einen vorhandenen OpenSfM-Job ohne neue Bildverarbeitung. Bei alten Jobs fehlt der Projektname im gespeicherten Manifest; die Anzeige bezeichnet die Dateizeit deshalb ausdrücklich als Berichtsstand. Ein COLMAP-Ordner wird abgelehnt.

Für den bereits abgebrochenen Lauf: im bisherigen Dialog **Ausgabeordner öffnen** anklicken und dessen exakten Ordnerpfad merken. Im aktualisierten Dialog **Lauf laden**, diesen Ordner auswählen, dann **Kennzahlen kopieren** und hier als Text einfügen. **RGB-Pilot starten ist dafür nicht erforderlich.** Die vorhandenen Ordner werden nicht umbenannt.

Die Kennzahlen ergänzen stored_depthmaps.raw/clean aus den vorhandenen Engine-Ausgabedateien. Nur Dateianzahlen, kein Bildinhalt und keine Integritäts-/Qualitätsfreigabe. Die Dateiendung .npz bedeutet im geprüften Enginezweig LZ4-verpackte Daten; vorhandene Ladefunktionen sind für eine spätere Prüfung maßgeblich. Noch keine automatische Fortsetzung, Zeitverlängerung oder Cachelöschung.

## Aktualisierter Startblock

Wird nach Windows-Abnahme mit fester Quell-ZIP und Prüfsumme bereitgestellt. Er öffnet den aktualisierten Dialog; danach nur **Lauf laden/Kennzahlen kopieren** verwenden. Kein neuer Bildlauf, Treiber-/Compiler-/Engine-Neubau oder Datenbankupdate.

## Prüfstand

Für diese Erweiterung lokal33 Tests bestanden, vier native Tk-Fälle auf Linux ohne Display übersprungen; native Prüfung der neuen Lauf-/Kopierbedienung noch offen. Der bisherige Pilotstand ist bereits technisch geprüft: Synthetische Tests verbinden alle zehn Stufen, Eingabeunveränderlichkeit, Teilmodell-Stopp, GPS-/Raster-Grenzen, Abbruch-/Zeitlimitstatus und sichere Kennzahlen. Ein tatsächlicher isolierter Pythonprozess prüft die dünne CLI-Delegation/cleanup gegen eine bewusst funktionslose Test-Engine; dies ist kein echter OpenSfM-/Bildtest. Quelle68f0f8e5: [Windows-CI42847018314](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42847018314) auf Python3.11 und3.12 vollständig bestanden, einschließlich tatsächlicher isolierter CLI-Prozesse mit Test-Engine sowie nativer Tk-Projektwahl/Start/Ergebnis-/Abbruchbedienung und synthetischem Job bis GeoTIFF. Kleine Erweiterung des vorhandenen Prozessstarters kapselt TEMP/TMP/MPL-Cache und deaktivierte VS-Telemetrie nur im Kindprozess, schon vor Conda-Aktivierung;36 bestehende Backendtests zusätzlich lokal bestanden. ZIP-SHA256 und fünf ausgelieferte Start-/Helper-/Service-Dateien bytegenau verglichen. Windows Server2022/Stub-Engine sind keine reale Windows10-/OpenSfM-/Flugbildabnahme; Nutzerlauf bleibt offen. Neuen Dokumentations-HEAD separat prüfen. Kein Kundenbild wurde hier verarbeitet.

Der gemeinsame Jobkern akzeptiert RGB-Datensätze und einen expliziten Engineaufruf; Datenbankwahl, Windows-Pfade und Tk bleiben im Desktopadapter. Für die spätere Onlinefassung ist derselbe Jobkern verwendbar. Jetzt keine zweite Web-/Cloudkette oder neue Engine, keine ODM/WebODM/ODX-Integration und kein Merge nach main. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).
