# PV-Hawk RGB-Modulerkennung: getrennter Windows-10-CPU-Pilot

Stand17.11.2026 · PV-HAWK-CPU-PILOT-01 · [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md)

Der Nutzer hat die zusätzliche isolierte Einrichtung ausdrücklich freigegeben und führt sie auf seinem Rechner selbst aus. Ziel dieses Schritts ist ein begrenzter Vergleich eines **tatsächlich vortrainierten RGB-Modulmodells** mit bereits gespeicherten passenden Umrissen. Noch keine automatische Gesamtparkverarbeitung oder Qualitätsfreigabe.

## Null KI-Kandidaten eingrenzen19.11.

Der Nutzerscreenshot zeigt **KI-Kandidaten:0** und acht gelbe gespeicherte passende Umrisse. Gelbe Umrisse sind die bisherige Teilreferenz, keine neuen KI-Treffer. Die passende Größe dieser Umrisse belegt daher noch keine KI-Erkennung. Der alte Bericht enthält keine Zwischenergebnisse; die Ursache ist damit nicht feststellbar.

Die aktualisierte Fassung protokolliert im selben einzelnen KI-Lauf reine Zähler: Modellregionen/Klassifikator vor der unveränderten0,7-Schwelle, gelieferte Instanzen, Masken-/Randprüfung, bestehende Geometrie-/Dublettenfilter und RGB-NoData. Modellregionen sind keine Modulanzahl. Keine Schwellen/Modelle/Bildgröße/Filter ändern, keine zusätzlichen Inferenzläufe automatisch starten. Das verbessert noch nicht nachgewiesen die Erkennungsanzahl; es grenzt die Ursache ein.

Der feste neue Aktualisierungsstart wird nach Prüfung ergänzt. Die bestehende KI-Installation bleibt erhalten. Danach:

1. Vorhandenen Thermal-Lauf13.11./18:58:37/oh9ptgy5 → RGB-Vergleich → denselben gespeicherten PV-Ausschnitt laden. Entwürfe/Notizen erhalten.
2. **Genau einmal KI-Modellvergleich starten(lokal)** mit vorhandener `E:\SolarCheck-PV-KI-Pilot\pv-hawk-rgb.LOCAL.json`. Kein neuer Orthofoto-/Matchinglauf.
3. Ergebnis öffnet sich mit Modell→Masken→Geometrie→RGB-Stufen. **KI-Kennzahlen kopieren(ohne Bilder und Pfade)** anklicken und ausschließlich diesen Text mitteilen. Er enthält keine Bildpixel/Koordinaten/Quellpfade/IDs/Notizen/Fingerprints. Noch keine Bilder/privaten Berichte hochladen.
4. Ergebnis schließen/wiederöffnen funktioniert ohne weitere KI-Berechnung. Alte Berichte bleiben lesbar; sie zeigen ausdrücklich „noch keine Filterkennzahlen“ und keine erfundenen Nullwerte. Ein reines Öffnen des alten Berichts liefert die neuen Zähler noch nicht.

Erst diese Kennzahlen entscheiden, ob das Modell selbst zu wenig liefert oder ob konkrete Filter Vorschläge verwerfen. Keine Module anhand erwarteter Anzahl hinzufügen und keine1000Einzelfreigaben verlangen. Unvollständigkeitslabel/Import-Sperre und sämtliche Fachfreigaben bleiben erhalten.

## Ergebnisanzeige aktualisieren ohne Neuinstallation

Der Nutzer bestätigt17.11., dass der KI-Modellvergleich im PV-Ausschnitt bereits ausgeführt wurde. Ein bestätigter Anzeigefehler kann das Ergebnis verbergen: Die bisherige Ergebnisansicht las die flachen PV-Hawk-Modellangaben wie eine verschachtelte ONNX-Beschreibung. Ein bereits erfolgreich berechneter Bericht kann trotzdem lokal gespeichert sein. Die korrigierte Oberfläche öffnet beide Berichtsformate, zeigt auch null KI-Kandidaten ausdrücklich an und bringt das Fenster nach vorn. Keine Änderung der gespeicherten Resultate oder Bilder.

In PowerShell diesen Block ausführen. Er lädt ausschließlich die korrigierte Quellfassung und öffnet die Oberfläche mit deinem vorhandenen F:-Python. **Keine Pakete/Gewichte neu installieren und keinen KI-Lauf starten.**

```powershell
$ErrorActionPreference = 'Stop'
$pilotCommit = 'dfb6bc9fc6a27fce5049da2f260bba071607d4e8'
$pilotStart = Join-Path 'E:\SolarCheck-PV-KI-Start' $pilotCommit
New-Item -ItemType Directory -Force -Path $pilotStart | Out-Null
$pilotZip = Join-Path $pilotStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pilotCommit" -OutFile $pilotZip
if ((Get-FileHash -Algorithm SHA256 $pilotZip).Hash.ToLowerInvariant() -ne 'e2a5d4685bc9e4c48d65cc6c96d46abaa869370fc860e885bdf7c21696eb4b04') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pilotZip -DestinationPath $pilotStart -Force
$pilotSource = Join-Path $pilotStart "MCM-SolarCheck-$pilotCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pilotSource 'scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py')
```

Geprüfte QuellZIP3061191Bytes/683Runtime-Python-Dateien bytegleich. Die vorhandene `E:\SolarCheck-PV-KI-Pilot`-Installation wird weiterverwendet. Nur die Oberfläche muss neu geöffnet werden.
 Danach vorhandenen Lauf13.11./18:58:37/oh9ptgy5 → RGB-Vergleich → gespeicherten PV-Ausschnitt öffnen → **Gespeicherten KI-Vergleich öffnen**. Bei vorhandener Datei keine erneute Modellberechnung nötig. Nicht erneut Entwürfe/Notizen speichern oder verändern, bevor der vorhandene KI-Vergleich geöffnet wurde: Sein Quellstand wird geprüft.

**Falls bisher nur der PowerShell-Einrichtungsstart lief:** Die CPU-Probe verwendet ein schwarzes synthetisches Bild und erzeugt keine Modulumrisse deiner Anlage. Dann im gespeicherten PV-Ausschnitt einmal **KI-Modellvergleich starten(lokal)** und `E:\SolarCheck-PV-KI-Pilot\pv-hawk-rgb.LOCAL.json` wählen. Das Ergebnis erscheint anschließend im eigenen Fenster: gelbe gespeicherte Teilreferenz, grüne KI-Kandidaten, Zähler darüber. **KI-Kandidaten:0 / Keine KI-Umrisse im Ergebnis** ist ein sichtbarer abgeschlossener Vergleich ohne übernommene KI-Umrisse; keine Aussage „alle Module gesund“ oder vollständige Anlagenabdeckung.

## Was eingerichtet wird

Ein eigener Ordner **`E:\SolarCheck-PV-KI-Pilot`** mit eigenem Python3.10-Environment, TensorFlow-CPU2.10.1/Keras2.10.0 und festgelegten Paketen aus [requirements-pv-hawk-cpu.txt](../requirements-pv-hawk-cpu.txt). Das vorhandene `E:\SolarCheck-OpenSfM\env\python.exe` dient nur zum Erstellen des eigenen Environments. Das bisherige F:-SolarCheck-Python, OpenSfM-Environment, Datenbank und sämtliche Bilder bleiben erhalten. Keine Administratorrechte, CUDA-, Compiler-, SDK- oder Docker-Installation nötig. Für Environment/Modell/Cache mindestens4GiB freien Platz auf E: einplanen(Linux-Vergleich2,2GiB); während der Einrichtung dort auch Paketcache/Temp. Internet nur für Einrichtung/öffentliche Downloads; Modellvergleich danach lokal.

Nur sechs festgelegte PV-Hawk-Quelldateien/Lizenz und die veröffentlichte **RGB-Gewichtsdatei mit244MiB** werden geladen. Keine Beispiele, Bilddatensätze oder Trainingsläufe. Alle Artefakte gegen festgelegte Größe/SHA-256 prüfen; beim erneuten Start geprüfte Dateien wiederverwenden. Abbruch mit Strg+C, danach denselben Start wiederholen. Bestehende fremde Zielordner ablehnen.

## Einmalige Einrichtung und Start

In **PowerShell** den gesamten Block ausführen. Er lädt eine feste Quellfassung, prüft deren SHA-256 und startet die zusätzliche Einrichtung. Anschließend öffnet er den Thermal-Dialog für deine bereits gespeicherten Ergebnisse. Keine neue Rekonstruktion starten.

```powershell
$ErrorActionPreference = 'Stop'
$pilotCommit = 'dfb6bc9fc6a27fce5049da2f260bba071607d4e8'
$pilotStart = Join-Path 'E:\SolarCheck-PV-KI-Start' $pilotCommit
New-Item -ItemType Directory -Force -Path $pilotStart | Out-Null
$pilotZip = Join-Path $pilotStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pilotCommit" -OutFile $pilotZip
if ((Get-FileHash -Algorithm SHA256 $pilotZip).Hash.ToLowerInvariant() -ne 'e2a5d4685bc9e4c48d65cc6c96d46abaa869370fc860e885bdf7c21696eb4b04') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pilotZip -DestinationPath $pilotStart -Force
$pilotSource = Join-Path $pilotStart "MCM-SolarCheck-$pilotCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pilotSource 'scripts\MCM_SolarCheck_PV_HAWK_SETUP.py')
if ($LASTEXITCODE -ne 0) { throw 'PV-Hawk-Einrichtung nicht abgeschlossen. Fehlermeldung beachten.' }
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pilotSource 'scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py')
```

QuellZIP3061191Bytes;683Python-Dateien unter src/scripts sowie Modell-Pin und Paketliste mit Repository bytegleich geprüft. Die Installation selbst legt ausschließlich den eigenen Pilotordner an. Modellgewichte sind nicht Teil der QuellZIP.

**Später erneut öffnen, ohne Installation/Downloads:**

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PV-KI-Start\dfb6bc9fc6a27fce5049da2f260bba071607d4e8\MCM-SolarCheck-dfb6bc9fc6a27fce5049da2f260bba071607d4e8\scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py'
```


Der Einrichtungsstart meldet vier Phasen: eigenes Environment, CPU-Pakete, Originalcode/RGB-Gewichte, echte Modellprobe auf einem synthetischen schwarzen RGB-Bild. Erst nach `status: passed` zum Bildvergleich wechseln. Ein schwarzes Bild ohne Treffer ist **kein Erkennungsqualitätsnachweis**. Bei Installations-/Downloadfehler Einrichtung erneut starten; bei wiederholtem Fehler nur die Fehlermeldung als Text mitteilen, keine privaten Bildpfade/Notizen. Paketliste und `cpu-probe.LOCAL.json` bleiben im Pilotordner.

## Erster lokaler Bildvergleich

1. Aktualisierten Thermal-Dialog öffnen und den vorhandenen Lauf **13.11.2026,18:58:37 / oh9ptgy5** laden. Keine neue Berechnung starten.
2. Gespeicherten RGB-/Thermal-Vergleich öffnen, danach gespeicherte **PV-Modul-Entwürfe**. Einen überschaubaren Ausschnitt mit einigen ganzen Modulen verwenden. Vorhandene passende Umrisse/Notizen lokal speichern; mindestens ein Umriss muss als **Umriss passt** gespeichert sein.
3. **KI-Modellvergleich starten(lokal)** → **`E:\SolarCheck-PV-KI-Pilot\pv-hawk-rgb.LOCAL.json`** wählen. SolarCheck startet ausschließlich das getrennte Pilot-Python. CPU-Vergleich maximal fünf Minuten; gleicher Knopf bricht ab. Das Ergebnis ersetzt keine vorhandenen Entwürfe.
4. Im Ergebnis **gelbe geprüfte Umrisse** mit **grünen KI-Kandidaten** vergleichen. Zähler sind nur für gespeicherte Teilreferenzen. Zusätzliche Kandidaten können echte bisher ungeprüfte Module oder Fehlvorschläge sein. Keine Genauigkeits-/Vollständigkeitsquote daraus ableiten. Zu klein/angeschnitten dargestellte Module im späteren Gesamtflächenweg gesondert behandeln; jetzt erst begrenzten Ausschnitt prüfen.
5. Ergebnis schließen und über **Gespeicherten KI-Vergleich öffnen** wiederöffnen. Keine erneute Inferenz nötig. Für einen Abbruchtest erneut starten/abbrechen; das letzte erfolgreiche Ergebnis und alle Entwürfe bleiben erhalten.

Nur als Text berichten: ganze Module im Ausschnitt, passende KI-Umrisse, fehlende Module, falsche/zu kleine/mehrfache Umrisse, angeschnittene Randmodule und ungefähre Dauer. Bilder, Koordinaten und private Berichte bleiben lokal. Noch keine tausend Einzelprüfungen durchführen: Diese kleine Stichprobe entscheidet über den nächsten Automatisierungsschritt.

## Herkunft, Anpassungen und Grenzen

- Original [PV-Hawk v1.0.0](https://github.com/LukasBommes/PV-Hawk/releases/tag/v1.0.0), Commit **af07a5e5690326837d1e9b26bdbb32f5582e89fd**; Code [MIT](https://github.com/LukasBommes/PV-Hawk/blob/af07a5e5690326837d1e9b26bdbb32f5582e89fd/LICENSE). Darin verwendeter Matterport-Code behält seine Copyright-/MIT-Hinweise. Keine gesamte PV-Hawk-Video-/SfM-Pipeline starten.
- Original RGB-Datei **mask_rcnn_pv_modules_rgb_0059.h5**,255858144Bytes, SHA-256 **8b862618a58dbd8b8f961d31c7d5dd0230293a013559182c4512780f7166c7d3**. Hashbestätigung belegt Identität, keine Feldqualität und keine zusätzliche Lizenz.
- Gewichte werden in die bekannte, hashgeprüfte ursprüngliche Modellarchitektur geladen; alle Inferenzschichten auf vollständige Gewichte/Form prüfen. Keine H5-Architektur-/Lambda-Deserialisierung. Originaldateien unverändert; Adapter verwendet TensorFlow-v1-Kompatibilitäts-API, Keras-Layeralias und zwei dynamische Shape-Korrekturen im Speicher. Original-PVConfig, RGB-Reihenfolge,512/640-Skalierung und Mittelwert129.4 erhalten. Instanzmasken zu gedrehten Rechtecken über vorhandene OpenCV-Geometrie, danach bestehende ROI-/NoData-/GIS-/Thermalmaskenprüfung. Scores≥0.7 sind Vorschläge, keine Freigabe. Die Original-PVConfig dient zunächst als Ausgangswert; Skalierung/Mittelwerte und übertragbare RGB-Erkennungsleistung müssen am lokalen Ausschnitt geprüft werden.
- Eigenständige Gewichts-/Trainingsdatenrechte sind für Produktion/Weiterverteilung nicht abschließend geklärt. Dies ist der ausdrücklich freigegebene technische Versuch; keine kommerzielle/distributive Gesamtfreigabe behaupten. Gewichte nicht in QuellZIP/Git übernehmen.
- Dauerlabel **unvollständig: 280 von 287 Bildern** und reguläre RGB-/Thermal-Paarimport-Sperre bleiben erhalten. Keine vollständige Abdeckung, unabhängige Geometriequalität, bestätigten physischen Modul-IDs oder Celsiuswerte. Fehlende Erkennung bedeutet nicht gesund.

## Prüfbelege

Linux/Python3.10: tatsächliche veröffentlichte RGB-Gewichte vollständig geladen, synthetische CPU-Inferenz bestanden(14,948s einschließlich Laden, schwarzes512×640RGB). Zusätzlich13Tests im getrennten Environment: echter Modellworker auf synthetischen georeferenzierten Bildern, Speicherung/Wiederöffnung, Fehlererhalt, Abbruch eines echten TF-Workers, Quellschutz, Artefakt-/Manifestgrenzen.147gezielte bestehende/erweiterte Tests grün, ein bewusst optionaler Modelltest außerhalb der isolierten Umgebung übersprungen. Frische Einrichtung unter Linux mit tatsächlichen Paket-/Code-/Gewichtsdownloads und Modellprobe bestanden(15,188s Modellprobe); nativer Windows2022-PV-Hawk-Job44159516437 bestanden: frische Einrichtung/ein echtes Modell/Syntheseprobe plus13Tests. Neue exakte HEAD-CI separat prüfen. Windows Server2022-CI ersetzt keine Abnahme auf dem Windows10-Auswerterechner; reale Erkennungsqualität und Laufzeit erst dort prüfen.

**Ergebnisanzeige-Korrektur17.11.:** Zwei synthetische PV-Hawk-GUI-Fälle(0/2Kandidaten) reproduzieren den ursprünglichen Fehler vor dem Fix; nach dem Fix öffnen fertiger Vergleich und gespeichertes Ergebnis ohne neue Inferenz und ohne Dateiveränderung. Fehlender Bericht nach reiner Einrichtung erklärt den nächsten Schritt.74gezielte Tests plus zwei Übergabeprüfungen grün; neue exakte HEAD-CI prüfen.
