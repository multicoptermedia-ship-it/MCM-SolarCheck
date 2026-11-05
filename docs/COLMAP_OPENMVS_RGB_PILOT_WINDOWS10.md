# Lokaler RGB-Pilot – COLMAP 3.12.6 und OpenMVS 2.4.0

**Aktueller Praxisstand 05.11.2026:** Der 26-Bilder-Test bleibt nach Basis, Fortsetzung und GUIDED unvollständig (GUIDED: 3/11/21). Diese Diagnose-/Parameterläufe sind abgeschlossen und werden nicht erneut empfohlen. Nutzer bestätigt brauchbare WebODM-Referenz aus größerem Bestand; bisher keine gleiche Datengrundlage. Nutzer meldet inzwischen je 287 RGB-/Thermalbilder und gestarteten lokalen Pilot; Endmeldung abwarten. Der Pilot berechnet RGB, Thermal-Erzeugung folgt später. Stufe/Laufzeit/Ergebnis und exakte Referenzidentität hier ungeprüft. Keine parallelen Wiederholungs-/Parameterläufe. Bisherige Befehle unten bleiben Entwicklungshistorie.

**Korrektur 05.11.2026:** Bei bereits installiertem OpenMVS 2.4.0 konnte der Pilot die Version fälschlich ablehnen, wenn Windows die Konsolenausgabe umleitet. Der aktualisierte Starter liest zusätzlich die frisch erzeugten OpenMVS-Werkzeuglogs im privaten Jobordner. Bestehende Installation, Python-Umgebung und Projektdatei behalten; nur den Pilot-Quellcode gemäß Abschnitt 2 aktualisieren. Tatsächlich andere oder nicht erkennbare Versionen werden weiterhin abgelehnt.

Der Nutzer hat diesen Pilot am 04.11.2026 bestätigt. Zielrechner: MEDION P17603, Windows 10, 64 GB RAM, Intel UHD 620 und NVIDIA MX250. Online später gegebenenfalls anpassen; jetzt den Offline-Weg praktisch belegen. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der neue Starter verarbeitet **alle bereits importierten RGB-JPGs eines ausdrücklich gewählten Projekts**. Er liest die vorhandene SQLite nur lesend, erstellt bytegleiche Arbeitskopien und einen neuen privaten Jobordner. Er verändert keine Originale, Projekt-/Thermaldateien oder Freigaben. Es ist ein separater Pilotstarter; das bisherige SolarCheck-Hauptfenster bekommt noch keinen neuen Menüpunkt. Bestehende Importe und Projekte weiterverwenden.

**Noch kein echter Windows-10-/RGB-/Thermal-Qualitätsnachweis.** Automatisierte Tests verwenden synthetische Dateien und simulierte Fremdprogramme; sie prüfen Dateireferenz, Prozessaufrufe, Speicherung und Abbruch. COLMAP/OpenMVS rechnen erst auf dem Rechner des Nutzers nach Klick auf „Pilot starten“. Der Pilot erzeugt zunächst nur RGB, kein Ersatz-Thermal und kein automatisch registriertes Rasterpaar.

## 1. Zwei Standardprogramme separat bereitstellen

Falls die Programme noch fehlen: Beide ZIPs manuell herunterladen und vollständig in getrennte Werkzeugordner entpacken, beispielsweise `E:\Tools\COLMAP-3.12.6` und `E:\Tools\OpenMVS-2.4.0`. DLLs/Plugins bei ihren Programmen lassen. Bestehendes MicMac bleibt unverändert. Der Pilot lädt/installiert keine Programme, Python-Pakete oder Treiber.

- **[COLMAP 3.12.6 Windows CUDA ZIP](https://github.com/colmap/colmap/releases/download/3.12.6/colmap-x64-windows-cuda.zip)**. Dieses Release verwendet CUDA 12.6.2 und ist der ältere GPU-Prüfkandidat für Pascal. COLMAP 4.2.1 mit CUDA 13.2 nicht als MX250-GPU-Version verwenden. Im Pilot die tatsächliche **`bin\colmap.exe`** auswählen, keine BAT-Datei.
- **[OpenMVS 2.4.0 Windows x64 ZIP](https://github.com/cdcseacave/openMVS/releases/download/v2.4.0/OpenMVS_Windows_x64.zip)**. Für diesen Pilot das normale CPU-ZIP verwenden. Später den Ordner auswählen, in dem `InterfaceCOLMAP.exe`, `DensifyPointCloud.exe`, `ReconstructMesh.exe`, `RefineMesh.exe` und `TextureMesh.exe` liegen; ein gemeinsamer `bin`-Unterordner wird ebenfalls gefunden.

Für den Pilot kein zusätzliches CUDA-Toolkit installieren; zunächst das vollständige COLMAP-Archiv verwenden. Die MX250-Version und der installierte Treiber sind hier noch nicht durch einen echten Programmstart geprüft. Der Starter prüft zunächst die Werkzeugversionen aus stdout und den jeweils frisch erzeugten, werkzeuggebundenen Logs im expliziten Jobordner. Frühere Joblogs oder andere Werkzeuglogs werden nicht als Versionsnachweis verwendet. Falls der GPU-Weg nicht startet, bleibt **[COLMAP 3.12.6 NoCUDA](https://github.com/colmap/colmap/releases/download/3.12.6/colmap-x64-windows-nocuda.zip)** mit deaktiviertem NVIDIA-Häkchen eine Alternative. Kein automatischer Treiberwechsel und kein Windows-11-Wechsel.

## 2. Pilot-Quellcode entpacken und starten

Den [festgelegten Pilot-Quellcode als ZIP herunterladen](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/archive/a5dcf8b0d8989f8d15717ab02757cc60fdbe37f8.zip) und in einen neuen Programmordner auf F: entpacken. Korrigierter Code-Stand `a5dcf8b0d8989f8d15717ab02757cc60fdbe37f8` (05.11.2026); die heruntergeladene Quellen-ZIP wurde hier geöffnet und Starter sowie beide Fachmodule byteweise gegen den Commit geprüft. Keine Fremdprogramm-Binaries wurden dafür heruntergeladen oder ausgeführt. Alten Programmordner, vorhandene Python-Umgebung und Datenbank behalten. Die Quellcode-ZIP enthält keine Fremdprogramm-Binaries oder Kundenbilder.

1. Das normale SolarCheck-Fenster schließen, damit während des Piloten keine Importe geändert werden.
2. Im **neu entpackten Ordner mit `src` und `scripts`** PowerShell öffnen.
3. Mit dem vorhandenen Python starten:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' '.\scripts\MCM_SolarCheck_RGB_PILOT.py'
```

Dieser Befehl startet den neuen Pilotdialog. Er verwendet Quellcode aus der neuen ZIP und Pakete aus der bestehenden Python-Umgebung; keine Installation/Migration. Der bisherige Schritt-115-Starter öffnet weiterhin seinen alten festgelegten Programmstand und ist nicht der Einstieg für diesen Pilot.

## 3. Vorhandenes Projekt ausdrücklich auswählen

Im Pilotdialog nacheinander wählen:

1. **Vorhandene Projektdatei:** dieselbe SolarCheck-SQLite mit dem bereits importierten Dachprojekt. Es wird keine neue leere DB angelegt. Nach der Dateiwahl das richtige Projekt aus der Liste wählen; es wird nicht automatisch das erste Projekt gestartet.
2. **COLMAP:** die `colmap.exe` der entpackten Version 3.12.6.
3. **OpenMVS:** den Programmordner der entpackten Version 2.4.0.
4. **Privater Ausgabeordner:** vorhandenen separaten Ordner, beispielsweise `F:\Auswertung-Pilot`. Er muss außerhalb von Originalbildordnern und Git liegen. Ergebnisse nicht in den Programmquellcode oder einen Cloud-Synchronisationsordner legen.
5. **Ziel-CRS:** zunächst leer lassen; aus den echten gespeicherten Kamerapositionen wird eine passende eindeutige WGS84-UTM-Zone bestimmt. Bei uneindeutiger Zone ein tatsächlich passendes metrisches Zielsystem angeben, kein geratenes EPSG. Originalhöhen werden erhalten; ihr Höhenbezug ist nicht unabhängig geprüft.
6. **Aktueller Auswerterechner, 05.11.2026:** NVIDIA-Häkchen entfernen. Der GPU-Versuch brach mit „CUDA driver version is insufficient for CUDA runtime version“ ab. Ohne Häkchen laufen COLMAP-Merkmale und Bildabgleich auf CPU; OpenMVS ist bereits CPU. Vorhandenes COLMAP-Paket/Projekt weiterverwenden, keine Neuinstallation erforderlich. CPU-Neustart/Ergebnis noch offen; keine bestimmte Treiberversion ungeprüft voraussetzen.

Für den ersten Vergleich ein kleines, zusammenhängendes, bereits importiertes Dachprojekt wählen. Keine neue ZIP-/EXIF-Inventur oder erneuter Import nötig. Auf **„Pilot starten“** klicken. Jetzt beginnt das Lesen/Kopieren der Original-JPGs. Importierte Kamerapositionen mit Länge/Breite/absoluter Höhe sind erforderlich; fehlende Werte werden nicht erfunden. Keine externe RGB-Kalibrierungsdatei oder RTK-Fix als allgemeine Startvoraussetzung.

Soll der Dialog bereits mit ausgeschaltetem NVIDIA-Häkchen öffnen, denselben vorhandenen Starter mit `--cpu` starten:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' '.\scripts\MCM_SolarCheck_RGB_PILOT.py' --cpu
```

Das ändert die Auswahl für diesen Start; kein neuer Download oder Import. Für das aktuelle CUDA-Treiberproblem zunächst diesen CPU-Weg verwenden. Ein Treiberwechsel ist dafür keine Voraussetzung. Die Rechenzeit kann steigen; der echte lokale Verlauf bleibt zu prüfen.

### Bereits angestoßener Bedienweg: vollständige Referenzserie (Gesamtlauf aktiv)

1. Im normalen SolarCheck separates leeres Testprojekt anlegen/aktivieren; alte Projekte behalten.
2. Import → **„Alternativ: DJI-Originalbilder auswählen (JPG, ohne ZIP)“**: gesamte RGB-Serie derselben brauchbaren Referenz auswählen. Vorhandener Originaldatei-Import, keine Archive neu inventarisieren. Thermal kann separat bleiben, Pilot liest nur RGB-Einträge.
3. Import abschließen, RGB-Anzahl prüfen, Hauptprogramm schließen.
4. Im vorhandenen Pilot gleiche SQLite-Datei **erneut auswählen** (Projektliste neu lesen), neues Testprojekt wählen, NVIDIA aus, bisherige Werkzeug-/Ausgabepfade verwenden, „Pilot starten“.

Vorhandener Starter mit `--cpu` möglich; kein neuer Download/Installer. Normaler Pilot-Code unverändert, GUIDED nicht als erfolgreicher Fix integriert. Mehr Bilder bedeuten längere CPU-Rechnung. Erst vollständige Registrierung/Namensmenge und echtes RGB-Orthofoto beurteilen. Zusätzliche Bilder könnten helfen, keine zugesicherte Lösung. Referenz bleibt manuell/extern, keine WebODM-Integration. Keine Originale/produktive DB/GPS hochladen.

## 4. Ablauf und gespeichertes Ergebnis

Der Dialog zeigt konkrete Stufennamen. Hauptschritte:

- COLMAP: Merkmale → Bildabgleich → Kameralösung → Vollständigkeitsprüfung → Positionsabgleich → Entzerrung.
- OpenMVS: COLMAP-Import → dichte Rekonstruktion → Oberfläche → Verfeinerung → Textur → Orthobild. Vorhandene Standardprogramme übernehmen diese Arbeit, keine neue eigene Engine.
- Rasterio/GDAL übernimmt das bereits gerenderte RGBA-PNG mit belegtem Rastertransform in **`rgb_ortho.tif`**. Keine neue Pixelorthorektifizierung oder erfundene Georeferenz.

Es wird nicht stillschweigend das größte Teilmodell gewählt: Wenn COLMAP mehrere getrennte Modelle oder nicht alle RGB-Aufnahmen ausrichtet, stoppt der Pilot vor der dichten Rekonstruktion. Eine einzige vollständige Kameralösung ist eine technische Mindestprüfung, keine Garantie richtiger Dachgeometrie.

Im neuen `rgb-pilot-…`-Job bleiben erhalten:

- **`rgb_ortho.tif`:** fertiges RGB-GeoTIFF, ausdrücklich ungeprüfte Darstellung. Mit IrfanView am lokalen Rechner öffnen; später vorhandenen GeoTIFF-Import verwenden.
- **`laufzeiten.json`:** Status, Bildanzahl, gesamte Laufzeit und Laufzeit pro Stufe; ohne Bildnamen, Quellpfade, Kamerakoordinaten oder rohe Prozessausgaben. Auch ein fehlgeschlagener Job bekommt diese Zusammenfassung.
- **`job.json`, `input-map.json`, `references.txt`, `alignment.txt`:** private lokale Herkunft/Koordinaten/Dateizuordnung; nicht nach GitHub/CI/Chat hochladen.
- **`step-….log` und weitere Werkzeugdateien:** private Rohprotokolle, Kameralösungen, Arbeitsbilder und Zwischenmodelle bleiben lokal. Nicht pauschal übertragen.

**„Ausgabeordner öffnen“** öffnet nach Erfolg den gespeicherten Job. Die alte MicMac-Paaranzeige im Hauptprogramm wird nicht automatisch ersetzt; das neue Pilot-TIFF direkt aus diesem Jobordner ansehen. Nach Schließen des Dialogs bleiben TIFF, Metadaten und Laufzeiten erhalten; für die Sichtprüfung nicht erneut rechnen. Der Pilot verändert die vorhandene Projektregistrierung nicht. Ein RGB-/Thermal-Paar wird erst nach erfolgreichem Thermal-Nachweis über den vorhandenen atomaren Paarimport übernommen.

**Abbrechen/Schließen während eines Laufs:** der eigene externe Prozessbaum wird beendet, der Dialog wartet auf die Beendigung. Keine Ergebnisübernahme oder Projektfreigabe; private Zwischenstände bleiben erhalten. Bei Fehlern nennt der Dialog nur die Stufe und relative Protokolldatei. Originale und Datenbank bleiben unverändert. Ein erneuter Start erzeugt einen frischen Job; kein automatisches Resume oder Überschreiben früherer Ergebnisse.

### Zwei RGB-Kameramodelle lokal vergleichen – 05.11.2026

Ordner sparse/0 und /1 bezeichnen zwei Rekonstruktionen, nicht RGB-/Thermalrollen. Der Pilot liest nur RGB-image_frames, keine thermal_frames. Mapperlog zuletzt 5/21 registrierte Frames; gespeicherte Größen/Überschneidung noch ungeprüft. Vorhandenes COLMAP liest beide Modelle ohne Überschreiben. Befehl wählt neuesten Job, prüft images.bin und filtert die Ausgabe auf Bildanzahlen/Abgleichstatus. Nur diese Zeilen teilen; komplette Ausgabe kann eine private Transformmatrix enthalten.

```powershell
$job = Get-ChildItem 'F:\Auswertung1' -Directory -Filter 'rgb-pilot-*' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $job) { throw 'Kein Pilotordner gefunden.' }
foreach ($modell in '0', '1') {
    if (-not (Test-Path -LiteralPath (Join-Path $job.FullName "sparse\$modell\images.bin") -PathType Leaf)) {
        throw 'Im neuesten Pilotordner fehlen die beiden gespeicherten Modelle.'
    }
}
$vorherigeFehleraktion = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & 'E:\Tools\colmap\bin\colmap.exe' model_comparer `
        --input_path1 (Join-Path $job.FullName 'sparse\0') `
        --input_path2 (Join-Path $job.FullName 'sparse\1') 2>&1 |
        ForEach-Object { "$_" } |
        Select-String 'Images:\s+\d+|Common images:\s+\d+|Reconstruction alignment failed'
} finally {
    $ErrorActionPreference = $vorherigeFehleraktion
}
```

Gemeinsame Bilder allein garantieren keinen geometrisch gültigen Merge. Erst bei konsistenter Geometrie COLMAP model_merger prüfen, danach weiterhin alle Projektbilder verlangen. Quellcodefalle: auch nach Merge failed kann model_merger ein Modell schreiben und Exitcode 0 liefern. Noch keine Zusammenführung oder Qualitätsfreigabe. Keine Bilder/Rohlogs/Modelle übertragen.

### Vergleich erledigt: vorhandenen Verbund einmal fortsetzen – 05.11.2026

Nutzerergebnis: 5/21 Bilder, 5 gemeinsame, Reconstruction alignment failed. Damit nur 21 unterschiedliche Bilder von 26 Eingaben; ein Merge ergänzt die fehlenden fünf nicht. Das Scheitern gilt für den standardmäßigen Reprojektionsabgleich, nicht automatisch als Qualitätsurteil über jede Pose. Keine Schwellen lockern oder Teilmodell als fertiges Gesamtbild verwenden.

Die [offizielle 3.12.6-FAQ](https://github.com/colmap/colmap/blob/3.12.6/doc/faq.rst) beschreibt mapper --input_path zur Fortsetzung mit weiteren Bildern/Triangulation. Folgender einmaliger lokaler Versuch läuft in PowerShell, nutzt vorhandene Merkmale/Matches/Arbeitsbilder und eine DB-Kopie, schreibt nur in einen neuen Versuchsordner. Es erfolgen keine neue Merkmalsextraktion und keine Änderung an Originalmodellen/DB. Aktuelle Pilot-GUI wird durch diesen separaten Versuch nicht automatisch fortgesetzt. CPU bleibt gesetzt. Mapper schreibt bei Fortsetzung direkt in den Zielordner, nicht in einen neuen Unterordner 0.

```powershell
$job = Get-ChildItem 'F:\Auswertung1' -Directory -Filter 'rgb-pilot-*' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $job) { throw 'Kein Pilotordner gefunden.' }
foreach ($datei in 'features.db', 'job.json', 'sparse\1\images.bin') {
    if (-not (Test-Path -LiteralPath (Join-Path $job.FullName $datei) -PathType Leaf)) {
        throw 'Im neuesten Pilotordner fehlen benoetigte Dateien.'
    }
}
$erwartet = (Get-Content -LiteralPath (Join-Path $job.FullName 'job.json') -Raw | ConvertFrom-Json).rgb_images
$versuch = Join-Path $job.FullName ('mapper-fortsetzung-' + [guid]::NewGuid().ToString('N'))
$modell = Join-Path $versuch 'modell'
New-Item -ItemType Directory -Path $modell -Force | Out-Null
$db = Join-Path $versuch 'features.db'
Copy-Item -LiteralPath (Join-Path $job.FullName 'features.db') -Destination $db
$vorherigeFehleraktion = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & 'E:\Tools\colmap\bin\colmap.exe' mapper `
        --database_path $db --image_path (Join-Path $job.FullName 'images') `
        --input_path (Join-Path $job.FullName 'sparse\1') --output_path $modell `
        --Mapper.num_threads 8 --Mapper.ba_use_gpu 0 --Mapper.multiple_models 0 `
        > (Join-Path $versuch 'mapper.log') 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'Fortsetzung fehlgeschlagen; mapper.log bleibt im neuen Versuchsordner.' }
    Write-Output "Erwartete RGB-Bilder: $erwartet"
    & 'E:\Tools\colmap\bin\colmap.exe' model_analyzer --path $modell 2>&1 |
        ForEach-Object { "$_" } |
        Select-String 'Registered images:\s+\d+|Mean reprojection error:'
    if ($LASTEXITCODE -ne 0) { throw 'Modellanalyse fehlgeschlagen.' }
} finally {
    $ErrorActionPreference = $vorherigeFehleraktion
}
```

Nur Erwartete RGB-Bilder/Registered images/Mean reprojection error mitteilen, keine mapper.log/Koordinaten übertragen. Erst bei vollständiger Registrierung exakte Namensmenge/Eingabesignaturen und Geometrie prüfen, bevor die bestehende Entzerrung/OpenMVS/GeoTIFF-Kette fortgesetzt wird. multiple_models=0 erzwingt keine fehlenden Zuordnungen und ist keine Freigabe. Kein fertiges Orthofoto oder reale Qualitätsabnahme aus diesem Versuch zugesichert. Falls weiterhin 21 Bilder: keine automatische Wiederholung derselben Diagnose-/Parameterläufe.

### Fortsetzung bleibt bei 21/26: ein geführter Abgleich – 05.11.2026

Fortsetzungsergebnis laut Nutzer: 21 registrierte Bilder bei 26 Eingaben, mittlerer Reprojektionsfehler 0.901954 px. Keine neue Aufnahme angeschlossen. Fortsetzung/Modellvergleich/Merge nicht wiederholen. Pixelrestfehler der rekonstruierten Beobachtungen ist kein Abdeckungs-/Boden-/Orthofoto-Nachweis.

Ein einzelner anderer Vergleich nach [offizieller COLMAP-FAQ](https://github.com/colmap/colmap/blob/3.12.6/doc/faq.rst): geometrisch geführter Bildabgleich (guided_matching). Vorhandene Merkmale wiederverwenden, berechnete Paarzuordnungen in neuer DB-Kopie erneuern. database_cleaner --type matches wirkt nur auf Kopie und erhält Bildmerkmale. Frischer mapper darf weiterhin mehrere Modelle liefern; keine Toleranzen lockern. CPU-Funktion im v3.12.6-Quellcode geprüft, keine reale Ausführung hier. Neuer Zielordner, Original-DB/Modelle/Arbeitsbilder erhalten. Keine neuen Programme/ZIPs/Feature-Extraktion erforderlich. Während der Berechnung werden nur feste Stufennamen und am Ende Kennzahlen angezeigt; Rohprotokolle bleiben lokal.

```powershell
$job = Get-ChildItem 'F:\Auswertung1' -Directory -Filter 'rgb-pilot-*' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $job) { throw 'Kein Pilotordner gefunden.' }
foreach ($datei in 'features.db', 'job.json') {
    if (-not (Test-Path -LiteralPath (Join-Path $job.FullName $datei) -PathType Leaf)) {
        throw 'Im neuesten Pilotordner fehlen benoetigte Dateien.'
    }
}
$erwartet = (Get-Content -LiteralPath (Join-Path $job.FullName 'job.json') -Raw | ConvertFrom-Json).rgb_images
$vergleich = Join-Path $job.FullName ('guided-vergleich-' + [guid]::NewGuid().ToString('N'))
$modelle = Join-Path $vergleich 'sparse'
New-Item -ItemType Directory -Path $modelle -Force -ErrorAction Stop | Out-Null
$testDb = Join-Path $vergleich 'features.db'
Copy-Item -LiteralPath (Join-Path $job.FullName 'features.db') -Destination $testDb -ErrorAction Stop
function Invoke-SolarCheckColmapTest {
    param([string]$Stufe, [string[]]$Argumente)
    Write-Output "COLMAP: $Stufe"
    & 'E:\Tools\colmap\bin\colmap.exe' @Argumente > (Join-Path $vergleich "$Stufe.log") 2>&1
    if ($LASTEXITCODE -ne 0) { throw "COLMAP-Stufe $Stufe fehlgeschlagen; Protokoll bleibt im Vergleichsordner." }
}
$vorherigeFehleraktion = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    Invoke-SolarCheckColmapTest '01-matchcache' @('database_cleaner', '--database_path', $testDb, '--type', 'matches')
    Invoke-SolarCheckColmapTest '02-guided' @('exhaustive_matcher', '--database_path', $testDb,
        '--SiftMatching.use_gpu', '0', '--SiftMatching.num_threads', '8', '--SiftMatching.guided_matching', '1')
    Invoke-SolarCheckColmapTest '03-mapper' @('mapper', '--database_path', $testDb,
        '--image_path', (Join-Path $job.FullName 'images'), '--output_path', $modelle,
        '--Mapper.num_threads', '8', '--Mapper.ba_use_gpu', '0')
    Write-Output "Erwartete RGB-Bilder: $erwartet"
    foreach ($teil in (Get-ChildItem -LiteralPath $modelle -Directory | Where-Object { $_.Name -match '^\d+$' })) {
        Invoke-SolarCheckColmapTest ('04-modell-' + $teil.Name) @('model_analyzer', '--path', $teil.FullName)
        Get-Content -LiteralPath (Join-Path $vergleich ('04-modell-' + $teil.Name + '.log')) |
            Select-String 'Registered images:\s+\d+|Mean reprojection error:'
    }
} finally {
    $ErrorActionPreference = $vorherigeFehleraktion
}
```

Nur Erwartete RGB-Bilder und pro Modell Registered images/Mean reprojection error teilen. Noch keine automatische Ergebnisübernahme: alle 26 Bilder und anschließend Namensmenge/Geometrie erforderlich. Erfolg offen. Falls weiterhin unvollständig, keine weitere blinde Parameterfolge; lokale Ursache gezielt klären. Kundenbilder, Quellnamen, Koordinaten und Rohlogs bleiben privat. Bestehender Pilot-Code unverändert; eine Integration des geführten Abgleichs erst anhand des Ergebnisses bewerten.

## 5. Lokale Abnahme vor weiterer Integration

Am neuen RGB-Ergebnis bei nativer Auflösung prüfen: vollständige Dach-/PV-Flächen, zusammenhängende gerade Modulränder, keine versetzten Fragmente/Doppelkonturen, sichtbare Datenlücken und plausibel belegte Lage. Anschließend mit dem unabhängig erzeugten WebODM-RGB vergleichen. Laufzeiten nur mit Bildanzahl, Recheneinstellungen und tatsächlichem Ergebnis vergleichen; keine Geschwindigkeit aus der NVIDIA-Karte allein ableiten.

Für eine erste Rückmeldung reichen Erfolg/Fehlerstufe und die nichtgeografische `laufzeiten.json`. Keine Original-JPGs, komplette Jobordner, produktive DB oder GPS-Dateien übertragen. Thermaldaten nicht als RGB oder ungeprüftes RGB nicht als Thermal registrieren. Keine Fach-/Temperatur-/Vermessungsfreigabe aus einem gültigen GeoTIFF-Header.

## Technischer Vertrag und spätere Online-Anpassung

`services/colmap_openmvs_pilot.py` hat keine Tk-/Qt-Abhängigkeit. `run_rgb_pilot(frames, config, …)` bekommt explizite Eingaben, Werkzeug-/Arbeitsverzeichnisse, Fortschritts-/Abbruchfunktionen und eine optionale Eingabesignaturprüfung. `read_rgb_project` ist ein getrennter SQLite-read-only-Adapter. Eine spätere Online-Worker-Anbindung kann autorisierte lokale Jobdateien und Ressourcen über dieselbe Schnittstelle liefern; derzeit keine Upload-/Cloud-Verarbeitung, Queue oder neue Online-API implementiert.

Georeferenz: tatsächliche WGS84-Kamerapositionen via installiertem PROJ offline in ein passendes metrisches Zielsystem, gemessene Positionen um einen gespeicherten lokalen Ursprung verschoben. COLMAP `model_aligner` passt ein globales Ähnlichkeitsmodell an diese Referenzen an. RANSAC-Entfernung 3 m ist ein ausdrücklich gespeicherter Ablehnungsparameter, **kein** behaupteter RTK-Fehler oder erfundenes GNSS-Gewicht. Keine Reparatur falscher lokaler Kamerageometrie durch einen CRS-Aufkleber. Große globale UTM-Koordinaten werden nicht in Float-Meshes weitergereicht.

Der Formatadapter `openmvs_orthomap.py` liest die tatsächlichen PLY-Vertices des zuletzt projizierten Meshes. OpenMVS-v2.4 definiert seine Bildgröße über die Float32-AABB mit 1,01-Rand, die maximal angeforderte Achse und den Mittelpunkt bei `(width−1)/2,(height−1)/2`. Die Kamera blickt entlang −Z, rechts ist +X, Bild-unten ist −Y. Daraus werden **nur Rastermetadaten** mit korrekter Pixelmitte→GDAL-Pixelecke gewonnen. PNG-Maße müssen genau passen; Alpha und gültige schwarze Pixel bleiben erhalten. Die gerundete TXT-Center-Datei allein wird nicht als Georeferenz verwendet. Kein Raytracing, Sampling, SfM, BA oder Meshrenderer in SolarCheck.

OpenMVS-Working-Archive werden nach dem COLMAP-Import ausdrücklich als Typ 2 gespeichert, damit die Oberfläche für die nächste Stufe erhalten bleibt. Koordinatennormalisierung wird ausgeschaltet. Texturierung erfolgt vor der Orthobild-Anforderung: Der v2.4-Quellzweig für eine direkte Orthomap-Anforderung auf untexturiertem Mesh kann die Texturierung überspringen. Der zweite Standardaufruf arbeitet deshalb auf dem tatsächlich texturierten Mesh; er kann je nach Binärstand erneut texturieren. Beide Laufzeiten werden sichtbar erfasst. Keine OpenMVS-Änderung/Fork oder neue Engine.

Parameter des ersten Piloten: COLMAP-SIFT maximal 2400 Pixel für Merkmalsextraktion, originale bytegleiche Arbeitskopien/Entzerrung; OpenMVS-Dichte/Verfeinerung Auflösungsstufe 1; Orthomap maximal 8192 Pixel; bis zu acht vorhandene CPU-Threads. Das sind Testeinstellungen, keine zugesicherte GSD/Genauigkeit. Quelle, Inputsignatur, lokaler Ursprung, tatsächlicher Rastertransform und Einstellungen bleiben im privaten Job gespeichert.

Primärquellen: [OpenMVS Windows-Konsole/Dateilog](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/Common/Log.cpp), [Versionsbanner](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/Common/Util.cpp), [COLMAP 3.12.6 CLI](https://github.com/colmap/colmap/blob/3.12.6/doc/cli.rst), [Positionsabgleich](https://github.com/colmap/colmap/blob/3.12.6/src/colmap/exe/model.cc), [OpenMVS TextureMesh](https://github.com/cdcseacave/openMVS/blob/v2.4.0/apps/TextureMesh/TextureMesh.cpp), [Orthoprojektion/Float-Mesh](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/MVS/Mesh.cpp), [Kamera-/Pixelkonvention](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/MVS/Camera.h), [AABB](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/Common/AABB.inl), [Kamerabasis](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/Common/Rotation.inl).

Release-SHA256 aus den offiziellen Release-Metadaten, keine hier ausgeführte Binärprüfung:

| ZIP | SHA256 |
| --- | --- |
| COLMAP 3.12.6 Windows CUDA | `bf9e01ba942df89d3dc561626e5a89300b0b09371afcdc33e17a60e9511cf081` |
| COLMAP 3.12.6 Windows NoCUDA | `7f79a1bfcaff25abdb1b264fe14328b6a573420a8efda2cc9ed7e97c867ec770` |
| OpenMVS 2.4.0 Windows x64 CPU | `0c31660c15c9ebc4c106873cf67564d9570d404aef7a6403451da1b6178b2167` |
