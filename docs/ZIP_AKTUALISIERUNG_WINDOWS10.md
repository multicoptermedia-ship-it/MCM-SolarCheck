# Windows-10-Testversion als ZIP aktualisieren

Der Nutzer startet bisher eine von ChatGPT bereitgestellte ZIP-Testversion auf Laufwerk **F:** über PowerShell. Ein Git-Checkout ist dafür nicht erforderlich. Windows 10 und die separat vorhandene MicMac-Installation bleiben erhalten.

## Gewünschter Schritt-115-Start aus Downloads

1. Bisherige GUI schließen. [Programm-ZIP des geprüften Standes herunterladen](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/archive/a0237d0a2339bda04efeb015ec65a10ae6c058d4.zip) und in **Downloads** lassen; nicht selbst entpacken oder umbenennen. Browserzusatz `(1)` ist erlaubt.
2. [Python-Startdatei herunterladen](../scripts/MCM_SolarCheck_Schritt115_START_MicMac.py) und als **`MCM_SolarCheck_Schritt115_START_MicMac.py`** ebenfalls in Downloads speichern (bei Quelltextanzeige „Link speichern unter“, Endung `.py`).
3. Den vom Nutzer vorgegebenen Block unverändert in PowerShell ausführen:

```powershell
$skript = Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "MCM_SolarCheck_Schritt115_START*.py" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $skript) {
    throw "Schritt-115-Startprogramm nicht im Downloadordner gefunden."
}

& "F:\MCM-SolarCheck\.venv\Scripts\python.exe" $skript
```

Die neu gespeicherte Datei muss die jüngste passende Startdatei sein. Sie verwendet dasselbe Python, entpackt nur Quellcode in **`F:\MCM-SolarCheck\test-updates\MCM-MicMac-a0237d0a2339`** und ruft dort den vorhandenen PowerShell-Starter auf. Danach die bisherige Projektdatei auswählen. Beim nächsten Start genügt der bereits vorbereitete Testordner; die ZIP muss dann nicht mehr vorhanden sein. Keine automatischen Downloads oder Installationen; MicMac bleibt separat. Der Programmstand ist absichtlich auf den bereits geprüften Stand festgelegt.

## Wenn der Orthofoto-Abschnitt nach dem Start fehlt

Der Abschnitt steht in diesem Programmstand direkt vor den Bildzählern auf Verarbeitung. Fehlt er vollständig, zunächst den tatsächlich gestarteten Stand klären. Alle SolarCheck-Fenster schließen, die oben verlinkte Python-Datei unter exakt `MCM_SolarCheck_Schritt115_START_MicMac.py` in Downloads speichern und direkt ausführen:

```powershell
$skript = Join-Path $env:USERPROFILE 'Downloads\MCM_SolarCheck_Schritt115_START_MicMac.py'
if (-not (Test-Path -LiteralPath $skript -PathType Leaf)) {
    throw 'MicMac-Startdatei fehlt unter dem angegebenen Namen in Downloads.'
}
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' $skript
```

Dadurch wird keine andere ältere Schritt-115-Datei aufgrund ihres Zeitstempels ausgewählt. Eine falsche Dateiauswahl ist bislang eine Hypothese. Bleibt der Abschnitt unsichtbar, den tatsächlich geladenen Programmquellpfad als nächsten Schritt prüfen; keine neue GUI oder Engine bauen.

## Neue ZIP mit vorhandenem Projekt starten

1. Bisherige SolarCheck-GUI schließen. Die aktuelle **Quellcode-ZIP dieses Feature-Standes** herunterladen. In einen **neuen Ordner auf F:** entpacken. Alten Testordner, bisherige Python-Umgebung und Projektdateien behalten. Die ZIP enthält weder Python-Pakete noch MicMac, Originalbilder oder produktive Datenbanken.
2. Den entpackten Programmordner öffnen, in dem **`scripts` und `src`** liegen. Dort PowerShell öffnen.
3. Den bestehenden Starter im Modus für das vorhandene Projekt aufrufen:

   ```powershell
   powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\scripts\start_windows10_offline.ps1 -UseExistingProject
   ```

4. In der Dateiauswahl die **bisherige SolarCheck-Projektdatei** wählen (`solarcheck.sqlite3` oder eine vorhandene `.sqlite`/`.db`). Die Standarddatei im Benutzerprofil wird, falls vorhanden, vorgeschlagen. Es wird keine neue leere Datenbank als Ersatz angelegt. Wenn die bisherige Datei unklar ist: abbrechen, nichts neu importieren oder überschreiben.
5. Der Starter verwendet ein bereits vorhandenes Python mit den SolarCheck-Abhängigkeiten. Fehlt eine geeignete Umgebung im neuen Ordner beziehungsweise im aktuellen Suchpfad, erscheint eine zweite Dateiauswahl für die bisherige **`python.exe`**, beispielsweise im alten Programmordner unter `.venv\Scripts\python.exe`. Die alte Umgebung wird weiterverwendet; keine Pakete werden automatisch installiert oder aktualisiert.

**Vor dem GUI-Start** wird die ausgewählte Datei nur lesend als SolarCheck-SQLite geprüft und daneben eine konsistente lokale Sicherung `…before-update-….sqlite3` erstellt. Diese berücksichtigt auch bereits bestätigte WAL-Daten. Erst nach erfolgreicher Sicherung darf die normale Anwendung eine ältere Datenbank öffnen/migrieren. Bei Abbruch, ungültiger Auswahl oder Sicherungsfehler wird die GUI für diese Datei nicht gestartet.

Die vorhandenen Projekte und Bildverweise bleiben an ihrem bisherigen Ort. Datenbank, Sicherung und Bilder bleiben ausschließlich auf dem Auswerterechner. Die neue Anwendung bezieht ihren Quellcode aus dem neu entpackten Ordner; die alte Python-Umgebung legt nicht den Programmstand fest.

## Danach den MicMac-Lauf beginnen

Vorhandenes Projekt öffnen → **Verarbeitung → „RGB- und Thermal-Orthofotos mit MicMac erstellen …“**. Als Programm `E:\Tools\MicMac\bin\mm3d.exe` und einen privaten Ausgabeordner außerhalb der Originale wählen. Dann **„Lokal erstellen“** starten.

Der vollständige Ablauf und der anschließende lokale Vergleich mit dem privat bereitgestellten WebODM-RGB-Orthofoto stehen in [MICMAC_SOLARCHECK_LOKALER_TEST.md](MICMAC_SOLARCHECK_LOKALER_TEST.md). Der tatsächliche Lauf und seine Bildqualitätsabnahme sind noch offen.

## Wenn Programm und Projektdatei bereits bekannt sind

Statt der Dateiauswahl unterstützt derselbe Starter explizite vorhandene Pfade:

```powershell
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\scripts\start_windows10_offline.ps1 -PythonExe '<BISHERIGE-PYTHON.EXE>' -DatabasePath '<BISHERIGE-PROJEKTDATEI.sqlite3>'
```

Das sind Platzhalter, keine angenommenen Nutzerpfade. Die Python-Umgebung muss bereits geeignet sein; der Starter bietet keinen automatischen Download- oder Installationsfallback. Ohne Zusatzparameter bleibt der bisherige normale Start aus der lokalen `.venv` erhalten.
