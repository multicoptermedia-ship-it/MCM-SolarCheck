# OpenSfM-eigener GPU-Matcher – kleiner Funktionstest

**OPEN-SFM-BUILD-01 beim Nutzer09.11.2026 bestanden. Nicht erneut bauen/installieren.** Neun native Module, Konstantentest und CLI-Registry PASS. Jetzt OPEN-SFM-GPU-01 in der vorhandenen Umgebung `E:\SolarCheck-OpenSfM\env`. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Die separate generische OpenCL-Prüfung ist abgeschlossen und wird nicht wiederholt. Dieser Test lädt die gebauten OpenSfM-Erweiterungen aus dem isolierten Prefix und ruft **deren eigenen OpenCL-Matcher** auf:64 künstliche Float32-Deskriptoren mit128 Dimensionen,32 KiB pro Eingabepuffer. Alle64 eindeutigen Identitätspaare müssen zurückkommen. Keine eigene Matcher-/Rekonstruktions-Engine, keine Fotos, Projekte oder SQLite, keine Paket-/Treiberinstallation. Nur als GPU ausgewiesene OpenSfM-Geräte zählen; CPU-Fallback liefert kein GPU-PASS. Indizes sind OpenSfM-eigen, nicht die Indizes der alten allgemeinen OpenCL-Prüfung. Der Upstream-Zweig kann Intel-GPUs ausblenden, wenn eine diskrete GPU vorhanden ist.

Eigener Kindprozess für Inventar und jeden GPU-Matchinglauf, je30 Sekunden begrenzt; Timeout/Abbruch beendet den eigenen Worker. Rohes Treiber-/Exception-Logging wird nicht als Bericht ausgegeben. Bericht enthält Gerätename/Speicher, Status und ggf. Fehlertyp/Workerexitcode, keine privaten Pfade. Kein Vollspeicher-/Dense-/Orthofotonachweis: `dataset` und `dense_reconstruction` bleiben `not_tested`.

Quelle der Upstream-API: v1.1/8b6b77ef, [GPU-Matcher](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/opensfm/src/lib/features/src/matching_opencl.cc), [Geräte-/Dense-Bindung](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/opensfm/src/lib/dense/depthmap_bind.h). Keine Quellcodeänderung an OpenSfM.

## In normaler PowerShell starten

Die kleine öffentliche Prüfdatei wird nach E: geladen und per SHA256 geprüft. TEMP/TMP gelten nur für diesen Aufruf und werden zurückgesetzt. Die bestehende Umgebung wird verwendet.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $pruefung = Join-Path $wurzel 'MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    $url = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/fcaf209854fdb13b5841f7685c5de78005c46732/scripts/MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $pruefung
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne 'd6316c3901057e9e8e7c376ff0855d6cc78b83d4bb6a23381b62f463df38a9cc') {
        throw 'Pruefdatei-Pruefsumme stimmt nicht.'
    }
    New-Item -ItemType Directory -Path "$wurzel\tmp" -Force | Out-Null
    $altTemp = $env:TEMP
    $altTmp = $env:TMP
    try {
        $env:TEMP = "$wurzel\tmp"
        $env:TMP = "$wurzel\tmp"
        & 'E:\Tools\Miniforge3\Scripts\conda.exe' run --no-capture-output --prefix "$wurzel\env" python -I $pruefung
    } finally {
        $env:TEMP = $altTemp
        $env:TMP = $altTmp
    }
}
```

Nur den letzten JSON-Block melden: `check: solarcheck-opensfm-gpu-1`, erwartet `status: passed` und unter mindestens einem GPU-Gerät `native_matching.status: passed`. Auch ein Fehler-/Timeout-JSON ist ein verwertbarer Befund; keine vollständigen lokalen Protokolle übertragen. Ein PASS bestätigt den kleinen nativen Matchingkernel, keine Dense-Rekonstruktion, Speicherreserve oder reale RGB-/Thermalqualität. Danach begrenzten lokalen RGB-Pilot planen, bestehende GeoTIFF-/PV-Funktionen weiterverwenden; Thermal bleibt Pflicht.

Lokal11 Adapter-/Protokolltests bestanden, darunter exakte kleine Eingaben, falsche Ergebnisse/CPU/native Fehler zählen nicht als PASS, Timeout und Workerprotokoll. Die Adaptertests führen keinen GPU-Kernel aus; tatsächlicher Nutzer-GPU-Befund bleibt offen. Die Windows-CI prüft den Wrapper mit synthetischen Adaptern, keine Hardware-/Fotoabnahme.
