# OpenSfM unter Windows 10 – getrennte Werkzeugverwaltung vorbereiten

> **Aktueller Nutzerbefund: conda 26.9.4 vorhanden, C++-Buildtools nicht vorhanden.** Keine weitere Miniforge-/OpenCL-/Compiler-Suchschleife. Der lokale Build ist noch nicht eingerichtet. Bevor zusätzlich proprietäre Compiler-/SDK-Werkzeuge installiert werden, die begrenzte Ausnahme zur bestehenden Softwarevorgabe ausdrücklich mit dem Nutzer klären.

## Konkrete, noch nicht ausgeführte Option

Für den vorgesehenen nativen Windows-Quellbuild kämen **Microsoft C++ Build Tools 2022** mit dem C++-Workload und Windows SDK infrage. Offizieller [Microsoft-Bootstrapper für Version 17/2022](https://aka.ms/vs/17/release/vs_BuildTools.exe); sein HEAD-Aufruf war erfolgreich, keine Binärdatei geladen/ausgeführt. Geplanter Umfang: C++-Buildtools/MSVC v143 für x64 und das benötigte SDK, ausschließlich zum Bauen der eigenständigen Open-Source-Abhängigkeit OpenSfM; keine zusätzliche proprietäre Orthofoto-Engine, kein komplettes Visual-Studio-IDE-Paket als Produktbestandteil. Keine automatische Installation oder Weitergabe der Microsoft-Tools.

Die [Microsoft-Lizenzseite](https://visualstudio.microsoft.com/license-terms/vs2022-ga-diagnosticbuildtools/) und das dort verlinkte offizielle Lizenzdokument (Update März 2024) wurden gelesen. Die Bedingungen erlauben ohne separate Visual-Studio-Produktlizenz das Kompilieren/Bauen erforderlicher C++-Abhängigkeiten unter OSI-Lizenz; OpenSfM ist eine solche Quellabhängigkeit. Diese Ausnahme ist kein generelles Recht zur beliebigen Entwicklung/Teständerung der Abhängigkeit. Microsoft-Tools selbst sind proprietär und lizenziert, nicht Open Source. Build-/SDK-/Redistributionsbedingungen nicht mit der BSD-Lizenz von OpenSfM gleichsetzen.

**Tatsächliche Vorgabenkollision:** REQ-ORTHO-03 im [Anforderungsprofil](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) sagt „Keine proprietären/kostenpflichtigen Programme“. Ein zusätzlicher lokaler Microsoft-Compiler/SDK benötigt daher eine ausdrücklich auf diesen Build begrenzte Nutzerausnahme. Eine kostenfreie Lizenz allein hebt diese Vorgabe nicht auf. Entscheidung offen; noch keine Download-/Installationsanweisung als freigegebenen nächsten Lauf ausgeben.

**Windows 10:** Die [aktuelle offizielle 2022-Systemmatrix](https://learn.microsoft.com/en-us/visualstudio/releases/2022/system-requirements) verweist auf OS-Lifecycle und gegebenenfalls ESU und ist keine pauschale Freigabe jedes Windows-10-Stands. Lokalen Installations-/Startweg und Zielkompatibilität vor einem echten Build gesondert qualifizieren; keinen Wechsel auf Windows 11 oder bezahltes OS-Upgrade verlangen. Der bereits bestandene kleine MX250-Kernel bleibt gültiger Befund, beweist diesen Buildweg aber nicht.


> **Aktueller Stand 07.11.: Miniforge erreichbar, `conda 26.9.4` vom Nutzer bestätigt.** Startmenü-Suche führte nur zur Webseite; direkter Aufruf der installierten conda.exe funktioniert. Installation nicht wiederholen, OpenCL ebenfalls bereits bestanden. Die ursprüngliche Installationsanleitung unten ist Historie. Jetzt vorhandene C++-Buildtools und SDK-Hinweis prüfen, bevor eine größere Buildumgebung installiert wird.

## Historie: vorbereitete Buildtools-Abfrage (Nutzer hat Fehlen inzwischen bestätigt)

Diesen rein lesenden Block in der vorhandenen PowerShell ausführen:

```powershell
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$cpp = ''
if (Test-Path -LiteralPath $vswhere) {
    $cpp = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationVersion
}
"C++-Buildtools: $(if ($cpp) { $cpp } else { 'nicht gefunden' })"
$sdk = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\Include'
"Windows-SDK-Ordner vorhanden: $(Test-Path -LiteralPath $sdk)"
```

Nur die zwei Ergebniszeilen zurückmelden. Es werden eine vorhandene MIT-lizenzierte Visual-Studio-Suchhilfe und ein Systemverzeichnis abgefragt; keine Kundenordner/Originale/SQLite gelesen, keine Compiler ausgeführt oder installiert. Kein PATH-/Profilwechsel. „Nicht gefunden“ bedeutet nicht, dass jeder mögliche eigene Compiler-/SDK-Pfad ausgeschlossen wurde. Der SDK-Ordner ist nur ein Installationshinweis, keine vollständige Header-/Bibliotheks-/Linkprüfung. Bei vorhandenen Werkzeugen deren tatsächlichen Start im späteren Build prüfen.

**Korrektur zur upstream Buildanleitung:** Die Aussage, der MSVC-Compiler komme bereits mit dem Conda-Paket `vs2022_win-64`, ist durch die konkreten Paketmetadaten nicht gedeckt. Das in upstream gelockte `anaconda/win-64/vs2022_win-64-19.44.35207-hc920ad0_12.tar.bz2` hat 18693 Bytes und hängt nur von `vswhere` ab; die Paketbeschreibung lautet „Activation and version verification of MSVC“. Auch conda-forge bietet eine kleine Aktivierungs-/Suchhilfe (25374 Bytes), keinen kompletten Compiler. Das ist ein realer zusätzlicher Buildbedarf, keine OpenCL-Störung.

Primärquellen: [upstream Windows-Buildbeschreibung](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/doc/building.md), [Metadaten des upstream Compiler-Aktivierungspakets](https://api.anaconda.org/package/anaconda/vs2022_win-64), [conda-forge-Paketmetadaten](https://api.anaconda.org/package/conda-forge/vs2022_win-64), [MIT-lizenziertes vswhere](https://github.com/microsoft/vswhere).

Die conda-forge-Windows-Metadaten belegen außerdem CPU-Builds von Ceres 2.2 und METIS/SuiteSparse. Ein späterer Umgebungsvorschlag muss CPU-Ceres auswählen, damit keine neue CUDA-Anforderung über den Solver entsteht, und BLAS-/Paketvarianten samt konkreten Lizenzen prüfen. Paketverfügbarkeit ist noch keine gelöste, gebaute oder gestartete OpenSfM-Umgebung. Noch keine Compiler-/SDK-Installation oder ungetestete Buildrezeptur weitergeben.


**OPEN-SFM-SETUP-01 · 07.11.2026, Miniforge noch nicht installiert.** [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md) · [OpenSfM-Quellenprüfung](OPENSFM_PRUEFUNG_2026-11-07.md).

## Bestätigter Ausgangspunkt

Der Nutzer hat die [OpenCL-Prüfung](OPENSFM_OPENCL_WINDOWS10.md) ausgeführt: Python 64 Bit, NVIDIA GeForce MX250, OpenCL und OpenCL C 1.2, Treiber 417.49, 2048 MiB GPU-Speicher und maximal 512 MiB je Allokation. Compiler verfügbar, kleiner CL1.2-Kernel korrekt gerechnet. Intel UHD Graphics 620 ebenfalls mit bestandenem Kerntest; deren gemeldete 26169 MiB sind kein dedizierter NVIDIA-Speicher. Windows 10 bleibt gesetzt.

**OpenCL-Prüfung abgeschlossen; nicht erneut verlangen.** Das Ergebnis rechtfertigt den nächsten Werkzeugschritt, ist kein Nachweis aller OpenSfM-Kernel, eines vollständigen Bildlaufs oder der Orthofoto-/Thermalqualität. Kein pauschaler Treiberwechsel.

Der Nutzer bestätigt: Miniforge, Miniconda und Anaconda sind noch nicht installiert. Vorhandenes SolarCheck-Python unter F:, SQLite, Originale und gestoppte Jobs erhalten.

## Historie: ursprüngliche Miniforge-Installation

1. Offiziellen [Miniforge3 26.9.4-2 Windows-x86_64-Installer](https://github.com/conda-forge/miniforge/releases/download/26.9.4-2/Miniforge3-26.9.4-2-Windows-x86_64.exe) herunterladen und selbst starten. Das ist die x86_64-Ausgabe für den bestätigten Rechner, nicht Windows-ARM64.
2. **Just Me** wählen. Vorgeschlagener eigener Ordner: **E:\Tools\Miniforge3**. Falls dort keine Schreibrechte bestehen, den angebotenen Benutzerordner verwenden; keinen vorhandenen SolarCheck-/Python-/Projektordner als Installationsziel wählen.
3. **Add Miniforge3 to my PATH environment variable** ausgeschaltet lassen. **Register Miniforge3 as my default Python** ebenfalls ausschalten. Die Startmenü-Verknüpfungen erstellen lassen; anschließend **Miniforge Prompt** öffnen.
4. Dort ausführen:

```bat
conda --version
```

Die angezeigte Versionszeile zurückmelden. Falls die Installation fehlschlägt, nur den kurzen Fehlertext ohne Benutzerpfade mitteilen. Kein `conda init`, kein Umbau der bestehenden F:-Umgebung und noch kein Kundendaten-/OpenSfM-Lauf in diesem Schritt.

Miniforge ist die getrennte Paket-/Umgebungsverwaltung. OpenSfM ist damit noch nicht installiert. Ein späterer OpenSfM-Build bekommt seine eigene Umgebung mit dem dafür gewählten Python, unabhängig vom Basis-Python von Miniforge und vom vorhandenen SolarCheck-Python.

## Geprüfte Quelle und Integrität

- Offizielles Projekt [conda-forge/miniforge](https://github.com/conda-forge/miniforge), Release [26.9.4-2](https://github.com/conda-forge/miniforge/releases/tag/26.9.4-2), veröffentlicht 06.11.2026.
- Installergröße laut Release: **158341784 Bytes**. SHA256 laut Release-Digest **und** separat gelesener offizieller [Prüfsummendatei](https://github.com/conda-forge/miniforge/releases/download/26.9.4-2/Miniforge3-26.9.4-2-Windows-x86_64.exe.sha256):

```text
9d83983669bc5d3b5dd4c631454bf953c3caf4ac78b9c9ada9971e5b021d83c3
```

- Optional lässt sich die lokal heruntergeladene Datei vor dem Start in PowerShell vergleichen:

```powershell
Get-FileHash (Join-Path $env:USERPROFILE 'Downloads\Miniforge3-26.9.4-2-Windows-x86_64.exe') -Algorithm SHA256
```

- Hier wurden nur öffentliche Release-Metadaten, Prüfsummendatei, README und Lizenz gelesen. **Installer nicht heruntergeladen oder ausgeführt**, keine Binärweitergabe durch SolarCheck.
- Das [offizielle README](https://github.com/conda-forge/miniforge#requirements-and-installers) nennt Windows x86_64 ab Windows 10; genaue Win10-Build-Kompatibilität muss der lokale Start zeigen.
- [Lizenz dieses Releases](https://github.com/conda-forge/miniforge/blob/26.9.4-2/LICENSE): Installer-Code BSD-3-Clause; mitgelieferte Pakete haben eigene OSI-Lizenzen. Miniforge verwendet laut README standardmäßig ausschließlich conda-forge. Das ist keine Lizenzfreigabe sämtlicher späterer OpenSfM-Abhängigkeiten.

## Nächster Teil nach bestätigtem Miniforge-Start

Den konkreten OpenSfM-Windows-Build separat qualifizieren, einschließlich Quellcommit, Paketquellen/-lizenzen, Compiler, OpenCL und lokaler CRS-Gitter. Das geprüfte upstream `conda-win-64.lock` enthält **72 conda-forge- und 100 anaconda-Kanalpakete**; es ist kein ausschließlich aus conda-forge stammender, von SolarCheck bereits geprüfter Build. Auch `conda.yml` nennt ausdrücklich `anaconda::metis`. Miniforge als Basis allein ändert diese expliziten Paketquellen nicht.

Diese Dateien deshalb nicht still als geprüfte reine conda-forge-Einrichtung starten. Eine neue Umgebungsrezeptur wäre zunächst zu lösen und technisch zu prüfen; hier wird noch keine ungetestete Ersatzrezeptur als funktionsfähig ausgegeben. Die konkrete Haupt-/Drittkomponentenlizenz und eventuelle Weitergabe bleiben vom normalen lokalen Werkzeugstart zu unterscheiden.

Nach erfolgreichem Build zuerst Werkzeug-/Kernelstart und vollständige dokumentierte GeoTIFF-Stufen ohne Kundenbilder prüfen. Danach einen bewusst lokalen RGB-Serienlauf und anschließend räumlich passendes Thermal qualifizieren; vorhandenen GeoTIFF-Import verwenden. Keine eigene Engine, keine ODM/WebODM/ODX-Integration und keine erneuten unveränderten MicMac-/COLMAP-Läufe.
