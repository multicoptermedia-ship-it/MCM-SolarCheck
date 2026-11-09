# Einmaliger Vergleich mit dem regulären OpenSfM-Importeinstieg

**Nutzerbefund09.11.2026:** GPU-Inventarworker schreibt JSON/worker_complete, danach0xC0000005. Windows meldet zweimal ntdll.dll10.0.19041.6456/Offset0000000000024785. Ntdll ist die Erkennungsstelle, kein Beleg einer defekten Windows-DLL oder eines bestimmten Treibers. Inventarergebnis vor Exit blieb bisher unbekannt. Compiler/SDK/Umgebung/Quellbau sind abgeschlossen, Windows-Logabfrage ebenfalls; nichts davon wiederholen. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der kleine bisherige Test importiert direkt NumPy/pyfeatures/pydense. Upstreams [bin/opensfm_main.py](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/bin/opensfm_main.py) importiert zuerst opensfm.commands. Der neue Vergleich mit `--cli-imports` übernimmt genau diesen Importeinstieg vor denselben nativen APIs. Kein DataSet-Objekt, keine Befehlsausführung/Bildserie oder geänderte Photogrammetrie. System32-Loader bleibt wie im letzten Versuch. Es ist ein einzelner kontrollierter Startvergleich, keine nachgewiesene Reparatur.

Jeder Worker30 s begrenzt, Prozessfehler bleibt FAIL. Nach gescheitertem Inventarexit kein Matching. Die nun erhaltenen before_exit-Fakten (Berichtsstatus, Geräte-/GPU-Anzahl, Fehlertyp) sind reine Diagnose und accepted_as_success false. Sie belegen auch bei reported_status completed noch keinen sicheren Betrieb. Erst bei sauberem Inventarexit testet der unveränderte OpenSfM-Matcher64 künstliche128-dimensionale Deskriptoren. Keine Fotos/SQLite, kein neuer Algorithmus, keine Installation/Registry-/PATH-Änderung. Bei erneutem Fehler keine weiteren Import-/Runtime-/Treibervarianten auf Verdacht, sondern nativen Stack gezielt eingrenzen; kein Early-Exit zur Umdeutung in PASS.

## Diesen vollständigen Block einmal in normaler PowerShell ausführen

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $pruefung = Join-Path $wurzel 'MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    $url = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/3367b3646d2cb33f48e2391e947c75509118c8af/scripts/MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $pruefung
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne 'bcdd2f249d6f37855ea5bdcbb8a761d03d121fec2ff1c947c525d0b44c693b6f') {
        throw 'Pruefdatei-Pruefsumme stimmt nicht.'
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

Den gesamten letzten JSON-Block melden, auch bei Fehler: `startup_mode: official_cli`, `loader_mode: system32_preload`; ggf. inventory.before_exit sowie last_stage/Exitcode. dataset/dense_reconstruction bleiben not_tested. Ein Conda-Fehlerhinweis nach JSON ist bei fehlgeschlagenem Probe-Exit erwartbar; keine vollständigen Rohlogs/Pfade/Dumps übertragen.

Quelle3367b364:24 lokale Adapter-/Protokolltests bestanden, darunter regulärer Registry-Import zuerst, Cachepflicht und Weitergabe des Startprofils an jeden isolierten Worker. Zwei Übergabetests bestanden; Windows-HEAD-CI separat prüfen. Diese Tests simulieren native Funktionen und beweisen keine GPU-/Fototauglichkeit. Nutzervergleich ist offen. Vorhandene GeoTIFF-/PV-/Thermal-Funktionen bleiben erhalten, beide echten Orthofotos und deren Qualität/Georeferenz/Laufzeit noch nachzuweisen.
