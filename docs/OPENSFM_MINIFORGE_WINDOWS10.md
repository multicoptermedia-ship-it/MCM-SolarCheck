# OpenSfM unter Windows 10 – getrennte Werkzeugverwaltung vorbereiten

**OPEN-SFM-SETUP-01 · 07.11.2026, Miniforge noch nicht installiert.** [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md) · [OpenSfM-Quellenprüfung](OPENSFM_PRUEFUNG_2026-11-07.md).

## Bestätigter Ausgangspunkt

Der Nutzer hat die [OpenCL-Prüfung](OPENSFM_OPENCL_WINDOWS10.md) ausgeführt: Python 64 Bit, NVIDIA GeForce MX250, OpenCL und OpenCL C 1.2, Treiber 417.49, 2048 MiB GPU-Speicher und maximal 512 MiB je Allokation. Compiler verfügbar, kleiner CL1.2-Kernel korrekt gerechnet. Intel UHD Graphics 620 ebenfalls mit bestandenem Kerntest; deren gemeldete 26169 MiB sind kein dedizierter NVIDIA-Speicher. Windows 10 bleibt gesetzt.

**OpenCL-Prüfung abgeschlossen; nicht erneut verlangen.** Das Ergebnis rechtfertigt den nächsten Werkzeugschritt, ist kein Nachweis aller OpenSfM-Kernel, eines vollständigen Bildlaufs oder der Orthofoto-/Thermalqualität. Kein pauschaler Treiberwechsel.

Der Nutzer bestätigt: Miniforge, Miniconda und Anaconda sind noch nicht installiert. Vorhandenes SolarCheck-Python unter F:, SQLite, Originale und gestoppte Jobs erhalten.

## Jetzt beim Nutzer manuell ausführen

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
