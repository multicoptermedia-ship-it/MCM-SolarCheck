# OpenSfM-Quellbau in der vorhandenen Windows-10-Umgebung

**OPEN-SFM-BUILD-01: Windows-CI bestanden, Nutzer-Windows10-Build offen.** Compiler-/SDK-Test und Abhängigkeitsprüfung sind beim Nutzer am08.11.2026 bestanden. Die Umgebung `E:\SolarCheck-OpenSfM\env` erhalten; nicht erneut einrichten. Keine Fotos, SQLite oder Rekonstruktion in diesem Schritt. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Unveränderter OpenSfM-v1.1-Quellcommit `8b6b77efddebf4429044d3206c7dc21c4e767e08`. Der von diesem Quellstand benötigte Khronos-OpenCL-C++-Header v2025.07.22 wird separat am Commit `2a608428f725cad7903ef55e1ce5b995895838f5` geladen; CMake erhält diesen lokalen Pfad, keine freie Tagauflösung beim Bauen. BSD-/Apache-Quellen, keine ODM/WebODM/ODX-Anbindung, keine eigenen Algorithmen. Öffentliche Quelltexte werden beim Einrichten geladen; spätere Bildverarbeitung muss offline bleiben.

Build mit vorhandenem VS2022/x64/v143-Generator und zwei parallelen MSBuild-Prozessen. Condas VS-Aktivierung setzt Plattform/Toolset; Ninja akzeptiert diese Parameter nicht (CI42517685656). Keine neue Compiler-/Paketinstallation und kein globaler PATH-/Python-Umbau. Pip verwendet vorhandene Abhängigkeiten ohne Index/Build-Isolation. Die intern noch angegebene Paketversion0.5.2 identifiziert nicht den geprüften v1.1-Quellstand.

[Windows-Quellbau42517970232](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42517970232), Quelle d8e6eb3c: Lockinstallation, unveränderter Engine-Quellbau, Wheelinstallation, OpenCL-Buildflag ON, neun native Module aus dem Prefix, Konstantentest und CLI-Registry bestanden. Keine GPU-Hardware/Fotoverarbeitung im CI. Zehn Vertragsfälle des exakten PowerShell-Blocks aus Quelle c38ad2a7 auf Windows/Python3.11 und3.12 bestanden; externe Werkzeuge dort inert, wirklicher Build separat wie oben. Eigener Win10-Quellbaunachweis bleibt offen.

**Nutzerbefund09.11.2026:** Git meldet dubious ownership/Exitcode128: Dateisystem auf E: speichert keine Besitzinformationen. ls-remote/Netzverbindung bestanden. Der Block ergänzt ausschließlich für seinen Prozess und dessen Kindprozesse zwei genaue safe.directory-Einträge für Source/OpenCL-Header; vorhandene Git-Prozesskonfiguration bleibt erhalten und wird vollständig zurückgesetzt. Keine globale Git-Konfigurationsdatei, kein Sternchen, keine ACL-/Dateisystemänderung oder TLS-Abschaltung. Damit gilt dieselbe begrenzte Freigabe auch für Git-Unterprozesse des Paketbaus. Vorhandenen Buildordner/Umgebung weiterverwenden; feste Quellcommits weiter prüfen. Die lange Buildordner-ID des Nutzers wird nicht im Repository gespeichert.

Fortsetzungsblock Quelle d62d5874: zwölf native PowerShell-Vertragsfälle auf Windows/Python3.11 und3.12 bestanden (42519812618), insbesondere Wiederaufnahme ohne Neuinitialisierung, Nichtverwendung abweichender Prüfdaten und keine Checkout-/Build-/Installationsfortsetzung nach fehlgeschlagenem Fetch/Commitnachweis. Öffentliche Tags erneut geprüft: beide zeigen die festgelegten Commits. Kein erneuter Enginebau nötig für diese reine Starteränderung; ursprünglicher nativer Baunachweis bleibt getrennt bestehen. Tatsächlicher Nutzerdownload/Build weiterhin offen.

## Lokaler Block – in normaler PowerShell

Ein vorhandener `build-<32 Hexzeichen>`-Ordner wird nur mit passender geprüfter buildcheck.py und Source-Gitordner wiederverwendet. Bei mehreren passenden Versuchen wird der zuletzt angelegte verwendet; keine beliebigen Privatordner. Ohne passenden Versuch neuer Buildordner auf E:. Quellen und Protokoll bleiben bei Fehlern erhalten; keine erzwungene Checkout-/Reset-/Clean-Operation. Eine bereits installierte OpenSfM-Paketmappe wird nicht überschrieben. Temporäre Prozessvariablen werden zurückgesetzt. F:-Python/Projekte bleiben erhalten.

<!-- tested-opensfm-source-build-start -->
```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $prefix = Join-Path $wurzel 'env'
    $conda = 'E:\Tools\Miniforge3\Scripts\conda.exe'
    $git = Join-Path $prefix 'Library\bin\git.exe'
    foreach ($datei in @($conda, $git, "$prefix\python.exe")) {
        if (-not (Test-Path -LiteralPath $datei -PathType Leaf)) { throw 'Vorhandene OpenSfM-Umgebung oder Miniforge fehlt.' }
    }
    if (Test-Path -LiteralPath "$prefix\Lib\site-packages\opensfm") { throw 'OpenSfM ist bereits vorhanden; bitte melden, nicht ueberschreiben.' }
    $hash = '426877f7135cc94669af14cd617a740e4f45808547f7037e1380e00e15990349'
    $altBuild = Get-ChildItem -LiteralPath $wurzel -Directory -Filter 'build-*' |
        Where-Object {
            $_.Name -match '^build-[0-9a-f]{32}$' -and
            (Test-Path -LiteralPath "$($_.FullName)\buildcheck.py" -PathType Leaf) -and
            (Test-Path -LiteralPath "$($_.FullName)\source\.git" -PathType Container) -and
            (Get-FileHash -LiteralPath "$($_.FullName)\buildcheck.py" -Algorithm SHA256).Hash -eq $hash
        } | Sort-Object CreationTime -Descending | Select-Object -First 1
    if ($altBuild) {
        $build = $altBuild.FullName
        Write-Host 'Vorhandener Buildordner wird fortgesetzt.'
    } else {
        $build = Join-Path $wurzel ('build-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $build | Out-Null
    }
    New-Item -ItemType Directory -Path "$wurzel\tmp","$wurzel\matplotlib" -Force | Out-Null
    $source = Join-Path $build 'source'
    $headers = Join-Path $build 'opencl-clhpp'
    $pruefung = Join-Path $build 'buildcheck.py'
    $url = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/1085a6ad774bd1a67c371c868b34853c8f95d462/scripts/MCM_SolarCheck_OPENSFM_BUILD_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $pruefung
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne $hash) { throw 'Buildpruefung-Pruefsumme stimmt nicht.' }
    $neu = @{ CONDA_PKGS_DIRS="$wurzel\pkgs"; TEMP="$wurzel\tmp"; TMP="$wurzel\tmp"; MPLCONFIGDIR="$wurzel\matplotlib"; PROJ_NETWORK='OFF'; CMAKE_GENERATOR='Visual Studio 17 2022'; CMAKE_BUILD_PARALLEL_LEVEL='2' }
    $gitCount = 0
    $vorherGitCount = [Environment]::GetEnvironmentVariable('GIT_CONFIG_COUNT', 'Process')
    if ($vorherGitCount -and -not [int]::TryParse($vorherGitCount, [ref]$gitCount)) { throw 'Ungueltige vorhandene Git-Prozesskonfiguration.' }
    if ($gitCount -lt 0) { throw 'Ungueltige vorhandene Git-Prozesskonfiguration.' }
    foreach ($repoPfad in @($source, $headers)) {
        $neu["GIT_CONFIG_KEY_$gitCount"] = 'safe.directory'
        $neu["GIT_CONFIG_VALUE_$gitCount"] = [IO.Path]::GetFullPath($repoPfad).Replace('\', '/')
        $gitCount++
    }
    $neu['GIT_CONFIG_COUNT'] = [string]$gitCount
    $alt = @{}
    foreach ($key in $neu.Keys) { $alt[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
    try {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $neu[$key], 'Process') }
        foreach ($record in @(
            @($source,'https://github.com/OpenSfM/OpenSfM.git','8b6b77efddebf4429044d3206c7dc21c4e767e08','refs/tags/v1.1','OpenSfM'),
            @($headers,'https://github.com/KhronosGroup/OpenCL-CLHPP.git','2a608428f725cad7903ef55e1ce5b995895838f5','refs/tags/v2025.07.22','OpenCL-Header')
        )) {
            if (-not (Test-Path -LiteralPath (Join-Path $record[0] '.git') -PathType Container)) {
                & $git init $record[0]
                if ($LASTEXITCODE -ne 0) { throw 'Quellordner konnte nicht angelegt werden.' }
            }
            Write-Host ('Quelltextdownload: ' + $record[4])
            & $git -C $record[0] fetch --depth 1 $record[1] $record[3]
            if ($LASTEXITCODE -ne 0) { throw ('Quelltextdownload ' + $record[4] + ' fehlgeschlagen, Git-Exitcode: ' + $LASTEXITCODE + '. Bitte die Git-Fehlerzeile davor beachten.') }
            $actual = & $git -C $record[0] rev-parse 'FETCH_HEAD^{commit}'
            if ($LASTEXITCODE -ne 0 -or $actual -ne $record[2]) { throw 'Quellcommit stimmt nicht.' }
            & $git -C $record[0] checkout --detach FETCH_HEAD
            if ($LASTEXITCODE -ne 0) { throw 'Quellstand konnte nicht aktiviert werden.' }
            $actual = & $git -C $record[0] rev-parse HEAD
            if ($LASTEXITCODE -ne 0 -or $actual -ne $record[2]) { throw 'Quellcommit stimmt nicht.' }
        }
        Write-Host 'OpenSfM wird auf E: kompiliert. Bitte PowerShell geoeffnet lassen.'
        & $conda run --no-capture-output --prefix $prefix python -m pip --log "$build\pip-build.log" wheel --no-deps --no-build-isolation --no-index --wheel-dir "$build\wheel" --config-settings=cmake.define.OPENSFM_BUILD_TESTS=OFF --config-settings=cmake.define.CMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF "--config-settings=cmake.define.FETCHCONTENT_SOURCE_DIR_OPENCLHEADERSCPP=$headers" --config-settings=build.tool-args=/m:2 --verbose $source
        if ($LASTEXITCODE -ne 0) { throw 'OpenSfM-Quellbau fehlgeschlagen; lokales pip-build.log erhalten.' }
        $cache = Get-Content "$source\build\CMakeCache.txt" -Raw
        if ($cache -notmatch '(?m)^OPENSFM_HAVE_OPENCL:BOOL=ON\s*$') { throw 'OpenCL-Unterstuetzung wurde nicht mitgebaut.' }
        $wheel = @(Get-ChildItem "$build\wheel" -Filter 'opensfm-*.whl' -File)
        if ($wheel.Count -ne 1) { throw 'Es wurde nicht genau ein OpenSfM-Paket erstellt.' }
        & $conda run --no-capture-output --prefix $prefix python -m pip install --no-deps --no-index $wheel[0].FullName
        if ($LASTEXITCODE -ne 0) { throw 'Installation des selbst gebauten Pakets fehlgeschlagen.' }
        & $conda run --no-capture-output --prefix $prefix python -I $pruefung
        if ($LASTEXITCODE -ne 0) { throw 'OpenSfM-Buildpruefung fehlgeschlagen.' }
    } finally {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $alt[$key], 'Process') }
    }
}
```

Nur den letzten JSON-Block zurückmelden. Erwartet: `check: solarcheck-opensfm-build-1`, `status: passed`, neun native Module aus dem isolierten Prefix, mathematischer Konstantentest und CLI-Registry bestanden. `dataset: not_tested` und `gpu_execution: not_tested` bleiben korrekt. Keine Fotos, Kundenpfade oder vollständigen Protokolle übertragen.

Der Test importiert die wirklichen Erweiterungen und die Upstream-Befehlsregistrierung; er rechnet keine Rekonstruktion und startet keinen GPU-Kernel. Erfolgreicher Build ersetzt weder einen begrenzten lokalen RGB-Pilot noch den Thermal-/GeoTIFF-Qualitätsnachweis. Das Quellpaket und der gemeinsame Python-Fachkern bleiben Grundlage für die spätere Online-Version; Windows-Buildadapter werden nicht in die Fachlogik übernommen.
