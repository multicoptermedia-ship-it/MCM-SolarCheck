# Windows-10-Testversion als ZIP aktualisieren

Der Nutzer startet bisher eine von ChatGPT bereitgestellte ZIP-Testversion auf Laufwerk **F:** über PowerShell. Ein Git-Checkout ist dafür nicht erforderlich. Windows 10 und die separat vorhandene MicMac-Installation bleiben erhalten.

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
