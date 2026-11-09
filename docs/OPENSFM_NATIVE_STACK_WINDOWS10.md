# Native OpenSfM-Absturz-Aufrufkette unter Windows 10

**OPEN-SFM-GPU-03 abgeschlossen09.11.2026:** Der reguläre CLI-Einstieg mit bestehendem System32-OpenCL erkennt ein Gerät/eine GPU und schreibt completed/worker_complete. Danach beendet sich der Worker mit0xC0000005. Kein Matching gestartet, keine GPU-Freigabe. Windows meldet ntdll.dll/Offset24785, ohne konkrete Ursache zu beweisen. Weitere Import-/Loader-/Treibervarianten sind kein nächster Schritt. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

**OPEN-SFM-STACK-01:** Ein kleiner Diagnoseadapter verwendet die vorhandenen Microsoft-Buildwerkzeuge und die Standard-Windows-APIs CreateProcess/WaitForDebugEvent/StackWalk64. Er kompiliert nur eigene neue Dateien in einem neuen stack-Ordner auf E:. Kein Installer oder Engine-Neubau. Nur der festgelegte Inventarworker wird gestartet, mit demselben --system-opencl/--cli-imports wie bisher. Keine Verbindung zu einem laufenden Fremdprozess, keine Matching-/Bild-/DB-Verarbeitung und keine Engineänderung.

Der Adapter hält den Prozess bei einer unbehandelten Ausnahme kurz an, liest mit Microsofts x64-Unwinder höchstens32 Stackframes und lässt die Ausnahme unbehandelt weiterlaufen. Der ursprüngliche Exitcode bleibt erhalten. Die Ausgabe enthält nur DLL-/Modulbasenamen und relative Offsets, keine absoluten Speicheradressen oder Pfade. Es wird kein Speicherabbild erstellt. Kindausgabe geht nach NUL, rohe Engineausgabe wird nicht gespeichert. Compilerlogs bleiben im eigenen neuen lokalen Diagnoseordner.

Symbolsuche: expliziter eigener leerer Ordner, Umgebungs-Symbolpfade und eingebettete PDB-Verweise ignoriert; kein Symbolserver/Download konfiguriert. Es werden nur lokale PE-/x64-Unwindinformationen verwendet. TEMP/TMP/MPLCONFIGDIR liegen im neuen E:-Ordner, PROJ-Netz aus. Inventarprozess30 s begrenzt, äußerer Diagnoseprozess40 s. Bei Timeout endet nur der eigene Prozess. Ein Debugger kann das Absturzverhalten beeinflussen; clean_exit unter Debugger wäre kein Beweis einer Reparatur.

Vor OpenSfM prüft der Adapter sich mit zwei eigenen synthetischen Prozessen: kontrollierter unbehandelter AV und normaler Exit. Erst bei erfolgreicher Stackaufnahme mit unverändertem AV-Exit und sauberem Vergleichsexit startet er den bekannten Inventarworker. diagnostic_complete bedeutet allein Diagnose abgeschlossen, accepted_as_gpu_success bleibt false. Teilweise/fehlende Frames sind möglich, insbesondere bei bereits entladenen Modulen; daraus keine konkrete Ursache erfinden.

## Diesen vollständigen Block einmal in normaler PowerShell ausführen

Die beiden kleinen Diagnosequelldateien werden aus fester Version geladen und vor Ausführung per SHA256 geprüft. Das vorhandene Inventarskript im bisherigen OpenSfM-Verzeichnis muss unverändert zur zuletzt ausgeführten Version passen; der Adapter prüft dessen Hash und überschreibt es nicht. Die vorhandene Umgebung/Installation bleibt erhalten.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $conda = 'E:\Tools\Miniforge3\Scripts\conda.exe'
    if (-not (Test-Path -LiteralPath "$wurzel\env\python.exe" -PathType Leaf)) {
        throw 'Vorhandene OpenSfM-Umgebung nicht gefunden; keine Neuinstallation starten.'
    }
    $startordner = Join-Path $wurzel ('stack-start-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $startordner | Out-Null
    $quelle = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/52440b601b2b8526ea65a4919ba045fc55627503/scripts'
    $dateien = @(
        @{ Name='MCM_SolarCheck_OPENSFM_STACK_PRUEFUNG.py'; Hash='ab677915eec6529c5f72a1578db13a0d0f97959f5752dfde7a045c92d343e2a9' },
        @{ Name='MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py'; Hash='6e2487b806740f9c7c5155214b2049650d36e614508cd334cbaef910e7ac4855' }
    )
    foreach ($datei in $dateien) {
        $ziel = Join-Path $startordner $datei.Name
        Invoke-WebRequest -UseBasicParsing -Uri "$quelle/$($datei.Name)" -OutFile $ziel
        if ((Get-FileHash -LiteralPath $ziel -Algorithm SHA256).Hash -ne $datei.Hash) {
            throw 'Diagnose-Pruefsumme stimmt nicht; keine Ausfuehrung.'
        }
    }
    New-Item -ItemType Directory -Path "$startordner\tmp","$startordner\matplotlib" | Out-Null
    $neu = @{ TEMP="$startordner\tmp"; TMP="$startordner\tmp"; MPLCONFIGDIR="$startordner\matplotlib"; PROJ_NETWORK='OFF' }
    $alt = @{}
    foreach ($key in $neu.Keys) { $alt[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
    try {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $neu[$key], 'Process') }
        $pruefung = Join-Path $startordner 'MCM_SolarCheck_OPENSFM_STACK_PRUEFUNG.py'
        & $conda run --no-capture-output --prefix "$wurzel\env" python -I $pruefung --root $wurzel
    } finally {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $alt[$key], 'Process') }
    }
}
```

**Nur den abschließenden JSON-Block zurückgeben.** Wichtig sind inventory_process.status, exception_code_hex, target_exit_code_hex und frames. Die vollständige Aufrufkette ist noch kein Ursachenbeweis: Modul/Offset zeigen die beteiligten Aufrufe; ohne Symbole sind keine Funktionsnamen verfügbar. Keine Logs, Pfade, Fotos oder Dumps hochladen. Falls die synthetische Eigenprüfung scheitert oder keine Frames verfügbar sind, meldet der Adapter dies; nicht auf eigene Faust weitere Startvarianten versuchen.

**Geprüfte Quelle52440b60:**37 lokale Adapter-/Protokolltests bestanden, ein nativer Test auf Linux übersprungen. [Windows-CI42686949559](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42686949559) hat auf Python3.11 und3.12 die tatsächliche Compile/Debug/Unwind-/Exit-/Timeout-Prüfung bestanden: mindestens zwei Frames samt eigenem Modul und Windows-Modul, ursprünglicher AV-Exit0xC0000005, sauberer Vergleichsexit0, eigener Timeout258, kein Dump/gefüllter Symbolordner. Windows Server2022 ist keine Windows-10-/GPU-Abnahme; der echte Nutzerbefund bleibt offen. Ganze CI-Workflows/aktuellen Dokumentations-HEAD separat prüfen.
