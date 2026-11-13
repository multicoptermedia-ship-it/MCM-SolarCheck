# OpenSfM: gezielter NVIDIA-Kompatibilitätsschritt unter Windows 10

**Abgeschlossen09.11.2026:** Nutzer bestätigt582.78 installiert und Rechner neu gestartet. Keine erneute Treiberinstallation oder Versionsfrage. Neuer Probe-Lauf endet beim CLI-Import nach30 s; GPU-API noch nicht erreicht. Weiter mit [getrennten Import-/Native-Zeitfenstern](OPENSFM_GPU_STARTZEIT_WINDOWS10.md). Die früheren Installations-/Startschritte darunter sind Historie.

## Belegter Stand vom 09.11.2026

**OPEN-SFM-STACK-01 abgeschlossen:** Nutzer meldet `native_capture_selftest: passed`, Inventarprozess `captured`, ursprünglicher Exit `0xC0000005`, 31 Stackframes, `unwind_stage: walking` und `unwind_error: 0`. Die Aufrufkette enthält beim Prozessende `pyfeatures.cp310-win_amd64.pyd`, C-Runtime, mehrere Aufrufe aus `nvopencl64.dll` und die Erkennungsstelle `ntdll.dll`/Offset24785. Damit ist NVIDIAs OpenCL-Pfad beteiligt. Es ist noch kein Beweis, ob der Ursprung ein Treiberfehler oder die Ressourcenlebensdauer im Zusammenspiel mit OpenSfM ist. Kein Matching gestartet; `accepted_as_gpu_success: false` bleibt richtig. Die native Stackdiagnose nicht erneut ausführen.

Die geprüfte unveränderte OpenSfM-Quelle v1.1 hält die Geräte/Kontexte/Befehlswarteschlangen in einem statischen `CLContext`. Das passt zu einer Freigabe beim Modul-/Prozessende. Ohne Funktionssymbole lässt sich die konkrete fehlerhafte Freigabe aus Modul/Offset allein nicht benennen. [CLDevice/CLContext](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/opensfm/src/lib/dense/opencl_utils.h).

Eine einfache Python-Konfigurationsänderung auf Intel ist kein belegter Ausweg: Derselbe C++-Code verwirft Intel-GPUs bei vorhandener diskreter GPU bereits vor der Python-Gerätewahl und erzeugt Kontexte für die verbleibenden Geräte. Die Konfiguration `opencl_ignore_intel_gpu_device: false` hebt diese C++-Filterung nicht auf. Auch ein CPU-Matcher wie FLANN ersetzt nicht die OpenCL-Dense-Kette dieses Zweigs. Keine weitere Loader-/Import-/Intel-/CPU-Variantenserie und keine Engineänderung vorbereiten.

## Nächster Schritt: manuelle Treiberaktualisierung

**OPEN-SFM-NVIDIA-01 vorbereitet, noch nicht beim Nutzer ausgeführt.** Zuletzt vom Nutzer gemeldet: NVIDIA417.49. NVIDIAs offizieller Suchdienst liefert am09.11.2026 für MX250/Windows10x64/DCH/WHQL:

| Merkmal | Geprüfte Herstellerangabe |
| --- | --- |
| Paket | GeForce Security Update Driver **582.78**, WHQL, DCH, Notebook |
| Veröffentlichung | 30.09.2026 |
| Unterstütztes Produkt | GeForce MX250, GeForce MX200 Series (Notebooks) |
| Betriebssysteme | OSList enthält Windows10 64-bit und Windows11; Windows11 ist keine Voraussetzung |
| Download | ca.912,74 MB, NVIDIA-Standalone-Paket |
| Details | [Offizielle NVIDIA-Seite 280047](https://www.nvidia.com/de-de/drivers/details/280047/) |

Quelle ist die explizite Modell-/OS-Liste im [offiziellen Suchdienst](https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/services/AjaxDriverService.php?func=DriverManualLookup&psid=113&pfid=894&osID=57&languageCode=1031&isWHQL=1&dch=1&sort1=1&numberOfResults=5), nicht nur dessen allgemeines oberstes OSName-Feld. Produkt-ID894 wurde über die [Hersteller-Produktliste](https://www.nvidia.com/Download/API/lookupValueSearch.aspx?TypeID=3&ParentID=113) als MX250 verifiziert. Die Detailseite ist erreichbar, ihre Produktdetails werden per JavaScript geladen. Kein Treiberpaket hier heruntergeladen oder ausgeführt.

NVIDIA empfiehlt bei Notebooks die vom Notebookhersteller geprüften Treiber; die öffentliche MX250-/OS-Liste ist keine Medion-spezifische Abnahme. Der bisherige Fehler ist in dieser Version nicht als behoben belegt. Der Schritt prüft eine konkrete neuere, unterstützte Treiberversion gegen die nachgewiesene Beteiligung des alten NVIDIA-Pfads.

1. Offene Arbeiten speichern und lokale Rechenläufe beenden. Über die offizielle Detailseite das **Notebook-Paket582.78 für Windows10 64Bit/MX250** nach E: laden.
2. Das Paket auf dem Auswerterechner selbst starten und die normale Grafiktreiberaktualisierung durchführen. Falls angeboten, reicht **NVIDIA-Grafiktreiber**; die NVIDIA-App ist für OpenSfM nicht erforderlich. Keine DLLs einzeln ersetzen, keine Treiberbereinigung oder Geräteabschaltung durchführen. Lehnt der Installer das konkrete Notebook ab, nur den kurzen Hinweis melden; nichts erzwingen.
3. Rechner neu starten. In **NVIDIA-Systemsteuerung → Systeminformationen** die installierte Version prüfen; erwartet582.78. Falls Windows die lange Versionsform zeigt, entspricht **32.0.15.8278** der NVIDIA-Version582.78.
4. **Erst nach bestätigter Aktualisierung/Neustart** den folgenden unveränderten kleinen OpenSfM-Test einmal ausführen. Keine Fotos oder Projektdateien erforderlich.

Es handelt sich um einen manuellen Schritt an der vorhandenen Hardwareplattform, keine neue Orthofoto-Engine oder Runtime-Bündelung in SolarCheck. Kein automatischer Treiberdownload/-start aus SolarCheck, kein Windowswechsel und kein OpenSfM-Neubau. Vorhandene Umgebung, F:-Python und SQLite bleiben erhalten. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

## GPU-Test nach dem Treiberwechsel

Dieser Block verwendet die zuletzt ausgeführte, unveränderte Prüfdatei und prüft ihren Hash vor dem Start. Er lädt keine neuen Pakete herunter. Die bekannte Probe führt erst nach fehlerfrei beendetem Inventar den OpenSfM-eigenen Matcher mit64 künstlichen Deskriptoren aus; jeder Prozessfehler bleibt FAIL. Ein bestandener kleiner Matcher ist noch kein Dense-/Speicherlast-/RGB-/Thermalnachweis.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $pruefung = Join-Path $wurzel 'MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne 'bcdd2f249d6f37855ea5bdcbb8a761d03d121fec2ff1c947c525d0b44c693b6f') {
        throw 'Vorhandene Pruefdatei passt nicht; nicht ausfuehren oder neu installieren.'
    }
    New-Item -ItemType Directory -Path "$wurzel\tmp","$wurzel\matplotlib" -Force | Out-Null
    $neu = @{ TEMP="$wurzel\tmp"; TMP="$wurzel\tmp"; MPLCONFIGDIR="$wurzel\matplotlib"; PROJ_NETWORK='OFF' }
    $alt = @{}
    foreach ($key in $neu.Keys) { $alt[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
    try {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $neu[$key], 'Process') }
        & 'E:\Tools\Miniforge3\Scripts\conda.exe' run --no-capture-output --prefix "$wurzel\env" python -I $pruefung --system-opencl --cli-imports
    } finally {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $alt[$key], 'Process') }
    }
}
```

Die bestätigte neue Treiberversion und nur den letzten JSON-Block melden. Bei erneutem Absturz keine weiteren GPU-/Treiber-/Startvarianten auf Verdacht und keinen Nachtlauf starten. Dann die bereits belegte OpenSfM-Sparse→OpenMVS-CPU-Schnittstelle gezielt als Alternative bewerten; noch kein gleichzeitiger Pilot/Installation und kein belegter vollständiger GeoTIFF-Weg. Der ältere Mapillary-Zweig allein ist kein nachgewiesener kompletter Orthofotoersatz. Keine eigene Engine. Beide Orthofotos sowie Georeferenz, Werteerhalt und Qualität bleiben das Ziel.

Die früheren Build-/Stackadapter bestanden bei Quellec65ec558 alle drei CI-Workflows einschließlich echter nativer Windows-Prüfung. Diese Dokumentation ändert keine Engine und beweist keine Reparatur auf dem Nutzergerät. Kein Merge nach main.
