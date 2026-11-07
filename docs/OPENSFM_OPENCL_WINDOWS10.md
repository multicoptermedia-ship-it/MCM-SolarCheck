# Nächster OpenSfM-Schritt: OpenCL unter Windows 10 prüfen

> **Nutzer-PASS 07.11.2026:** MX250 und Intel UHD 620 haben den kleinen Kernel bestanden, Python 64 Bit. MX250: 2048 MiB GPU-Speicher/512 MiB Allokationsgrenze. Prüfung abgeschlossen, nicht wiederholen. Nächster Schritt ist die [getrennte Miniforge-/OpenSfM-Einrichtung](OPENSFM_MINIFORGE_WINDOWS10.md); kein OpenSfM-/Orthofoto-PASS daraus.

**OPEN-SFM-OPENCL-01 · 07.11.2026.** Nach der [Quellenprüfung beider OpenSfM-Versionen](OPENSFM_PRUEFUNG_2026-11-07.md) zuerst den vorhandenen GPU-Rechenweg qualifizieren. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md). Zielrechner bleibt Windows 10, MX250/UHD 620, vorhandenes F:-Python; kein erneuter MicMac-/COLMAP-Nachtlauf.

## Der jetzt bedienbare Schritt

1. [MCM_SolarCheck_OPENCL_PRUEFUNG.py](../scripts/MCM_SolarCheck_OPENCL_PRUEFUNG.py) über den geprüften Quelllink im aktuellen Chat als gleichnamige Datei in Downloads speichern. Auf GitHub kann die Datei über „Download raw file“ heruntergeladen werden. Es ist ein einzelnes Skript ohne Zusatzpakete.
2. PowerShell öffnen und ausführen:

```powershell
$pruefung = Join-Path $env:USERPROFILE 'Downloads\MCM_SolarCheck_OPENCL_PRUEFUNG.py'
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' $pruefung
```

3. Die angezeigte Ausgabe zurückmelden. Sie enthält ausschließlich Python-Bitness, GPU-Namen, Anbieter, OpenCL-/Treiber-/Compilerangaben, Speichergrößen und Testergebnisse/Fehlercodes. Keine Originalbilder, Projektdateien, GPS-Daten oder vollständigen Treiberlogs übertragen.

Das Skript benötigt weder SolarCheck-Hauptfenster noch OpenSfM-Installation, keine Adminrechte und keine Python-Zusatzpakete. Es lädt nichts herunter, installiert/ändert keine Treiber und öffnet keine Bilder oder SQLite. Der PowerShell-Download des eigenen Quellskripts ist ein ausdrücklich vom Nutzer ausgeführter Vorbereitungsschritt, kein automatischer Fremdsoftware-Installer.

## Was tatsächlich geprüft wird

Der vorhandene Windows-OpenCL-Loader wird ausschließlich aus System32 geladen. Das Skript fragt GPU-Geräte (keine OpenCL-CPU-Ersatzgeräte), Compilerstatus und GPU-Speicher ab. Pro GPU wird ein kleiner OpenCL-C-1.2-Kernel kompiliert, ausgeführt und sein Ergebnis mit vier bekannten Ganzzahlen verglichen. Ressourcen werden anschließend freigegeben.

Native Treiberaufrufe laufen in eigenen kurzlebigen Kindprozessen: maximal 20 Sekunden pro Geräteabfrage bzw. pro GPU-Test. Timeout oder Strg+C beendet und wartet auf den eigenen Worker. Fremde mm3d-/COLMAP-/Python-Prozesse werden nicht gesucht oder beendet. Fehlerausgaben beschränken sich auf feste Operationsnamen/Codes; beliebige Treibertexte und lokale Pfade werden nicht ausgegeben. Kein Aufnahme-/Datenträgerinventar, kein Ergebnisupload.

## Ausgabe richtig lesen

- `kernel_test.status: passed` bedeutet: genau dieses GPU-Gerät hat den kleinen Kernel korrekt gerechnet.
- MX250/NVIDIA und Intel getrennt betrachten. Ein bestandener Intel-Test allein bedeutet nicht, dass die OpenSfM-Standardkonfiguration Intel verwendet; sie überspringt Intel-Geräte standardmäßig.
- `python_bits` dokumentiert den benutzten Interpreter. Der vorgesehene OpenSfM-Werkzeugbuild ist win-64; die vorhandene SolarCheck-Umgebung wird dafür nicht umgebaut.
- `memory_mib` und `max_allocation_mib` sind GPU-Grenzen; die vorhandenen 64 GB System-RAM ersetzen keinen GPU-Speicher.
- `opensfm: not_tested` gilt auch bei bestandenem Kernel. Der Test bestätigt weder alle OpenSfM-Kernel noch Bildserien-Speicherbedarf, Rekonstruktionsqualität, Laufzeit, Thermal-Radiometrie oder GeoTIFF-Korrektheit.
- Fehlender Loader, keine Plattform/GPU, Buildfehler, falsches Ergebnis oder Timeout bleiben sichtbare Befunde. Keine stillen Treiberinstallationen, CPU-Ausweichalgorithmen oder Parameterexperimente.

## Danach in vertikalen Schritten

Nach Auswertung dieses konkreten Ergebnisses den eigenen OpenSfM-Werkzeugbuild getrennt von SolarCheck vorbereiten: Quellcommit, Komponenten-/Paketbedingungen und Offline-CRS-Gitter festhalten, dokumentierte CLI-Stufen vervollständigen. Das mitgelieferte Windows-run_all.bat nicht blind verwenden. Werkzeug-/Kernelstart und GeoTIFF-Kette zunächst ohne Kundendaten prüfen.

Erst dann einen bewussten lokalen Nutzerlauf mit vollständiger zusammengehöriger RGB-Serie vorsehen. Abnahme an zusammenhängenden Dach-/PV-Flächen, scharfen Modulgrenzen, voller Abdeckung, echter Rasterreferenz und gemessener Laufzeit; vorhandenen GeoTIFF-Import wiederverwenden. Danach geometrisch passendes Thermal und Werteerhalt prüfen und vorhandene PV-/Thermal-/Review-/Berichtskette fortführen. Keine eigene Photogrammetrie oder ODM/WebODM/ODX-Integration.

## Technischer Testumfang

Tests verwenden eine synthetische OpenCL-Bibliothek für erfolgreiche Rechnung, Ressourcenfreigabe, native Fehler und falsche GPU-Ergebnisse. Zusätzlich ein echter isolierter Python-Worker und ein wirklich gestarteter/bei Timeout beendeter Warteprozess. Keine echte GPU oder OpenSfM-Rekonstruktion in diesen Tests. Windows-CI führt die Prüfung separat auf Python 3.11/3.12 aus; fehlende GPU auf dem Runner wird als Befund behandelt, nicht als bestandener Hardwaretest. Nutzerabnahme unter Windows 10 weiterhin offen.
