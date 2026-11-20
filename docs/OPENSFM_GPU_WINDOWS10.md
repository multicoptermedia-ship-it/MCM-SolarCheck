# OpenSfM-eigener GPU-Matcher – kleiner Funktionstest

**Neuester Stand09.11.2026:** Stackdiagnose abgeschlossen; NVIDIA-OpenCL beim Prozessende beteiligt. Keine weitere unveränderte Start-/Loaderprobe. [Gezielter manueller Kompatibilitätsschritt](OPENSFM_NVIDIA_WINDOWS10.md) ist jetzt der Einstieg; untenstehende frühere Aufträge sind Historie.

**OPEN-SFM-BUILD-01 beim Nutzer09.11.2026 bestanden. Nicht erneut bauen/installieren.** OPEN-SFM-GPU-01 ist dagegen beim Inventar mit worker_failed/3221225477=0xC0000005 abgebrochen, ohne Matching-/Fotoergebnis. Genaue native Stelle und ursprünglicher DLL-Pfad sind unbekannt. OPEN-SFM-GPU-02 ist ein einmaliger Runtimevergleich in derselben vorhandenen Umgebung `E:\SolarCheck-OpenSfM\env`. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).


**Aktueller Stand:** System32-Vergleich ebenfalls mit0xC0000005 nach worker_complete und vollständigem JSON beendet. Der alte Elternbericht enthält nur dessen Existenz, nicht dessen Ergebnis; keine erfolgreiche GPU-Erkennung daraus ableiten. Windows-Absturzbericht inzwischen erhalten: ntdll.dll/0xC0000005, Ursache offen. Nächster einmaliger Schritt: [regulären OpenSfM-Importeinstieg vergleichen](OPENSFM_STANDARDSTART_WINDOWS10.md). Den Runtimevergleich darunter vorerst nicht erneut starten. Ein geplanter GPU-Test ist keine Freigabe des bisherigen Ergebnisses.
Die separate generische OpenCL-Prüfung ist abgeschlossen und wird nicht wiederholt. Dieser Test lädt die gebauten OpenSfM-Erweiterungen aus dem isolierten Prefix und ruft **deren eigenen OpenCL-Matcher** auf:64 künstliche Float32-Deskriptoren mit128 Dimensionen,32 KiB pro Eingabepuffer. Alle64 eindeutigen Identitätspaare müssen zurückkommen. Keine eigene Matcher-/Rekonstruktions-Engine, keine Fotos, Projekte oder SQLite, keine Paket-/Treiberinstallation. Nur als GPU ausgewiesene OpenSfM-Geräte zählen; CPU-Fallback liefert kein GPU-PASS. Indizes sind OpenSfM-eigen, nicht die Indizes der alten allgemeinen OpenCL-Prüfung. Der Upstream-Zweig kann Intel-GPUs ausblenden, wenn eine diskrete GPU vorhanden ist.

Eigener Kindprozess für Inventar und jeden GPU-Matchinglauf, je30 Sekunden begrenzt; Timeout/Abbruch beendet den eigenen Worker. Rohes Treiber-/Exception-Logging wird nicht als Bericht ausgegeben. Bericht enthält Gerätename/Speicher, Status und ggf. Fehlertyp/Workerexitcode, keine privaten Pfade. Kein Vollspeicher-/Dense-/Orthofotonachweis: `dataset` und `dense_reconstruction` bleiben `not_tested`.

Quelle der Upstream-API: v1.1/8b6b77ef, [GPU-Matcher](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/opensfm/src/lib/features/src/matching_opencl.cc), [Geräte-/Dense-Bindung](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/opensfm/src/lib/dense/depthmap_bind.h). Keine Quellcodeänderung an OpenSfM.

## Einmaliger Vergleich mit vorhandenem Windows-OpenCL

Die frühere erfolgreiche allgemeine Probe lud OpenCL gezielt aus System32; welche DLL der abgestürzte OpenSfM-Worker verwendet hat, ist unbelegt. Der neue Aufruf mit `--system-opencl` lädt die vorhandene System32/OpenCL.dll vor NumPy/OpenSfM in jedem frischen Worker und prüft ihren Modulpfad über Windows-APIs. Bereits außerhalb von System32 geladene OpenCL-DLL wird abgelehnt. Keine DLL ersetzen/umbenennen, keine Paket-/Treiberinstallation oder PATH-/Registryänderung. Nur den eigenen Prozess betreffender Laufzeitvergleich, noch keine bestätigte Fehlerursache oder Reparatur.

Feste Fortschrittsmarken unterscheiden Systemloader, Modulimporte, Dense-/Features-Geräteabfrage, Metadaten, Matching und Workerabschluss. Der Elternprozess gibt bei Crash/Timeout nur bekannte Stufen, Exitcode/Hex und die Information aus, ob bereits ein strukturierter Bericht geschrieben wurde. Auch nach geschriebenem Ergebnis führt ein nativer Prozessabsturz weiterhin zu FAIL; ein Absturz beim Beenden wird nicht als GPU-PASS verborgen. Keine privaten Treiberpfade/Stacktraces im Bericht. Matching startet nur nach erfolgreich abgeschlossenem Inventar, weiterhin nur mit künstlichen Deskriptoren.

## Bereits ausgeführter Runtimevergleich – vorerst nicht wiederholen

Die kleine öffentliche Prüfdatei wird nach E: geladen und per SHA256 geprüft. TEMP/TMP gelten nur für diesen Aufruf und werden zurückgesetzt. Die bestehende Umgebung wird verwendet.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $pruefung = Join-Path $wurzel 'MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    $url = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/db09361dd9cd151b873ee6677670e7846ebc7714/scripts/MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $pruefung
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne 'c9569add6279bbc01aa1d72a335dac7cbce0fdb5ff6f52900a27287b339bf87e') {
        throw 'Pruefdatei-Pruefsumme stimmt nicht.'
    }
    New-Item -ItemType Directory -Path "$wurzel\tmp" -Force | Out-Null
    $altTemp = $env:TEMP
    $altTmp = $env:TMP
    try {
        $env:TEMP = "$wurzel\tmp"
        $env:TMP = "$wurzel\tmp"
        & 'E:\Tools\Miniforge3\Scripts\conda.exe' run --no-capture-output --prefix "$wurzel\env" python -I $pruefung --system-opencl
    } finally {
        $env:TEMP = $altTemp
        $env:TMP = $altTmp
    }
}
```

Nur den letzten JSON-Block melden: `check: solarcheck-opensfm-gpu-1`, nun `loader_mode: system32_preload`; erhofft `status: passed` und unter mindestens einem GPU-Gerät `native_matching.status: passed`. Auch ein Fehler-/Timeout-JSON ist ein verwertbarer Befund; keine vollständigen lokalen Protokolle übertragen. Ein PASS bestätigt den kleinen nativen Matchingkernel, keine Dense-Rekonstruktion, Speicherreserve oder reale RGB-/Thermalqualität. Danach begrenzten lokalen RGB-Pilot planen, bestehende GeoTIFF-/PV-Funktionen weiterverwenden; Thermal bleibt Pflicht.

Lokal19 Adapter-/Protokolltests bestanden, zusätzlich Loader-Reihenfolge/Modulpfadprüfung mit simulierten Windows-APIs, feste Absturzstufen und kein PASS nach Shutdown-Absturz. Keine echte GPU-Ausführung im CI; Quelle37576c37 der ersten Probe hatte alle drei CI-Läufe bestanden, Nutzer-GPU-Test dennoch FAIL. Neue HEAD-CI separat prüfen. Die Adaptertests führen keinen GPU-Kernel aus; tatsächlicher Nutzer-GPU-Befund bleibt offen. Die Windows-CI prüft den Wrapper mit synthetischen Adaptern, keine Hardware-/Fotoabnahme.


Nachträgliche Berichtskorrektur: Bei einem künftigen nativen Absturz bewahrt die Probe ausschließlich einen begrenzten before_exit-Status, Geräte-/GPU-Anzahl und bekannten Fehlertyp. Diese Diagnosefakten sind accepted_as_success false; selbst eine zuvor fertige Inventarliste startet nach Prozessabsturz kein Matching. Lokal21 Adapter-/Protokolltests bestanden, tatsächliche Ursache weiter offen. Noch keinen erneuten GPU-Lauf zur Gewinnung dieser Felder verlangen; zuerst den bestehenden Windows-Fehlermoduleintrag verwenden.
