# OpenSfM-Abhängigkeiten auf Windows 10 einrichten

**OPEN-SFM-ENV-01 · 08.11.2026.** Compiler-/Windows-SDK-Test beim Nutzer bestanden. Miniforge ist vorhanden. Diese Einrichtung ergänzt eine getrennte Umgebung; SolarCheck auf F:, QGIS/Erweiterungen, Arduino und Projekte bleiben erhalten.

## Geprüfter Stand

[Windows-Qualifikation 42513503105](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42513503105): tatsächliche Installation aus einem Explicit-Lock, 22 isolierte Bibliotheksimporte und GeoTIFF-Treiberprüfung bestanden. Installierte Paket-URLs/Prüfsummen stimmen mit dem Lock überein. Der festgeschriebene Repository-Lock wurde zusätzlich im Windows-Lauf42514749322 installiert und geprüft; alle vier Workflows am Quell-HEAD f28bfae3 erfolgreich. 293 Pakete, ca. **508,5 MiB Paketdownloads**, entpackter Platzbedarf zusätzlich. Python3.10.22, OpenCV4.12.0, NumPy2.2.6, GDAL3.11.4, pyproj3.7.1, igraph1.0.0. CPU-Ceres2.2/OpenBLAS, kein CUDA/MKL. Git gehört zur Umgebung; kein gesonderter Git-Installer oder MCM-Git-Checkout erforderlich.

[Festgeschriebener Windows-Lock](../config/opensfm/conda-win64-explicit.lock) ausschließlich conda-forge/win-64/noarch. [Candidate-Rezept](../config/opensfm/conda-win64-specs.txt) dient nur bewusstem späteren Aktualisieren; der Nutzerlauf löst keine neuen Versionen auf. Ziel für den späteren Quellbau ist OpenSfM v1.1, Commit `8b6b77efddebf4429044d3206c7dc21c4e767e08`.

**Das ist noch kein gebautes OpenSfM und kein Orthofoto-/GPU-/Thermal-Nachweis.** Reale Windows10-Nutzerprüfung08.11.2026 bestanden: status passed, Python3.10.22,22 isolierte Importe, GeoTIFF-Treiber verfügbar und PROJ-Netz aus. Umgebung eingerichtet, nicht erneut installieren. Server2022-CI und Nutzerbefund sind getrennte Nachweise. Als Nächstes folgt der [getrennte Quellbau](OPENSFM_QUELLBAU_WINDOWS10.md) in genau dieser vorhandenen Umgebung. Gemeinsame SolarCheck-Fachlogik für Offline/Online bleibt erhalten; dieser Windows-Lock ist betriebssystemspezifisch.

## Einmaliger Start in normaler PowerShell

Der Block lädt nur den festgelegten Lock und die kleine Prüfdatei nach E:, prüft deren SHA256, erstellt eine **neue** Umgebung unter `E:\SolarCheck-OpenSfM\env` und führt danach die Bibliotheksprüfung aus. Vorhandene Zielumgebung wird nicht verändert; bei entsprechender Meldung nicht löschen, sondern Ergebnis einordnen. Keine Administratorrechte, kein conda init oder globaler Python-/PATH-Umbau. Temporäre Prozessvariablen werden auch bei Fehlern zurückgesetzt. Keine Originalbilder/SQLite, keine Rekonstruktion oder Uploads.

<!-- tested-opensfm-environment-start -->
```powershell
& {
    $ErrorActionPreference = 'Stop'
    $conda = 'E:\Tools\Miniforge3\Scripts\conda.exe'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $umgebung = Join-Path $wurzel 'env'
    if (-not (Test-Path -LiteralPath $conda -PathType Leaf)) { throw 'Miniforge-Programm nicht gefunden.' }
    if (Test-Path -LiteralPath $umgebung) { throw 'Zielumgebung existiert bereits; bitte melden, nicht loeschen.' }
    New-Item -ItemType Directory -Path $wurzel,"$wurzel\pkgs","$wurzel\tmp","$wurzel\matplotlib" -Force | Out-Null
    $quelle = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/f28bfae35c13007e4aa4dd8f4320b42ddf029e3b'
    $lock = Join-Path $wurzel 'conda-win64-explicit.lock'
    $pruefung = Join-Path $wurzel 'MCM_SolarCheck_OPENSFM_UMGEBUNG_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri "$quelle/config/opensfm/conda-win64-explicit.lock" -OutFile $lock
    Invoke-WebRequest -UseBasicParsing -Uri "$quelle/scripts/MCM_SolarCheck_OPENSFM_UMGEBUNG_PRUEFUNG.py" -OutFile $pruefung
    if ((Get-FileHash -LiteralPath $lock -Algorithm SHA256).Hash -ne 'beaa873a45ec24f1d801b81ab11b3190cdbd6aa4b53dcf77e5ebadaf4468c890') { throw 'Lock-Pruefsumme stimmt nicht.' }
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne 'e48316f5e1a5cdc28471928dd71279cf64620859f5fe76a549db24ad2821d2cf') { throw 'Pruefdatei-Pruefsumme stimmt nicht.' }
    $neu = @{ CONDA_PKGS_DIRS="$wurzel\pkgs"; TEMP="$wurzel\tmp"; TMP="$wurzel\tmp"; MPLCONFIGDIR="$wurzel\matplotlib"; PROJ_NETWORK='OFF' }
    $alt = @{}
    foreach ($schluessel in $neu.Keys) { $alt[$schluessel] = [Environment]::GetEnvironmentVariable($schluessel, 'Process') }
    try {
        foreach ($schluessel in $neu.Keys) { [Environment]::SetEnvironmentVariable($schluessel, $neu[$schluessel], 'Process') }
        Write-Host 'Abhaengigkeiten werden auf E: installiert. Das kann einige Minuten dauern.'
        & $conda create --yes --prefix $umgebung --file $lock
        if ($LASTEXITCODE -ne 0) { throw 'Umgebungseinrichtung fehlgeschlagen.' }
        & $conda run --no-capture-output --prefix $umgebung python -I $pruefung
        if ($LASTEXITCODE -ne 0) { throw 'Umgebungspruefung fehlgeschlagen.' }
    } finally {
        foreach ($schluessel in $neu.Keys) { [Environment]::SetEnvironmentVariable($schluessel, $alt[$schluessel], 'Process') }
    }
}
```

Zurückmelden nur den letzten JSON-Block: `check: solarcheck-opensfm-env-1`, erwartet `status: passed`, `modules_from_isolated_prefix: 22`, `geotiff_driver: available`, `proj_network: disabled`. `opensfm: not_built` ist in diesem Schritt richtig. Bei Installationsfehler keine Kundenpfade oder vollständigen Logs übertragen; Zielumgebung/Cache erhalten, nicht pauschal entfernen.

## Herkunft und Grenzen

Quellfassung der Installationsdateien: `f28bfae35c13007e4aa4dd8f4320b42ddf029e3b`. Lock33945 Bytes/SHA256 `beaa873a45ec24f1d801b81ab11b3190cdbd6aa4b53dcf77e5ebadaf4468c890`; Prüfdatei3051 Bytes/SHA256 `e48316f5e1a5cdc28471928dd71279cf64620859f5fe76a549db24ad2821d2cf`. Der Lock ist die geprüfte CI-Paketliste, ergänzt um Herkunftskommentare und normalisierte Zeilenenden. Jede Paket-URL enthält die vom Conda-Solver bereitgestellte MD5; der Startblock schützt zusätzlich die kompletten Quelldateien per SHA256.

Paketmetadaten umfassen FOSS-Lizenzen und die zum Windows-Build gehörenden Microsoft-VC/UCRT-Plattformlaufzeiten. OpenVINO-Ausgabemetadaten haben teils leere Lizenzfelder; das offizielle [conda-forge-Rezept](https://github.com/conda-forge/openvino-feedstock/blob/main/recipe/meta.yaml) nennt Apache2.0 und Drittkomponenten-Lizenzdateien. Dies ist eine lokale Abhängigkeitsinstallation, keine pauschale Weitergabefreigabe für ein SolarCheck-Paket. Die begrenzte Microsoft-Buildtools/SDK-Freigabe ist dokumentiert, nicht erneut abfragen.

CI testet standardmäßig den festgeschriebenen Lock. Bewusstes späteres Aktualisieren über workflow_dispatch/refresh_lock erzeugt einen neuen Lösungsvorschlag als Artefakt; nicht automatisch beim Nutzer übernehmen. Noch kein OpenSfM-C++-Quellbau oder echter Bildlauf, keine Änderung am bestehenden GeoTIFF-/PV-/Thermal-Import.

Der exakte PowerShell-Startblock wurde mit inertem Download/Conda auf Windows/Python3.11/3.12 aus Quelle0c0bf252 geprüft: Erfolg und fünf Fehler-/Existenzfälle, Hashprüfung, kein Start nach Downloadfehler, kein Überschreiben vorhandener Umgebung und Rücksetzung der Prozessvariablen. Dort werden keine echten Pakete installiert; die tatsächliche Paketinstallation/Importprüfung ist der separate oben genannte CI-Lauf. Reale Win10-Nutzerausgabe am08.11. ebenfalls PASS erhalten; dieser Block ist abgeschlossen. PROJ-Netzsperre gilt im Prüfprozess; beim späteren Engine-Aufruf muss die Offline-Konfiguration erneut ausdrücklich gesetzt und benötigte Grids müssen lokal bereitgestellt werden.
