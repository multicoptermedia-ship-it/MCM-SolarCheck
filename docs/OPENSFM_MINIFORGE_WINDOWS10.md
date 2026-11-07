# OpenSfM unter Windows 10 – Buildwerkzeuge vorbereiten

**OPEN-SFM-SETUP-01 · Nutzerfreigabe 07.11.2026.** [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md) · [OpenSfM-Quellenprüfung](OPENSFM_PRUEFUNG_2026-11-07.md).

## Aktueller Stand und abgegrenzte Freigabe

- Miniforge erreichbar: Nutzer bestätigt `conda 26.9.4` per direktem PowerShell-Aufruf. Kein Neuinstallieren wegen fehlendem Startmenü-Shortcut.
- OpenCL-Nutzertest abgeschlossen: 64-Bit-Python; GeForce MX250, CL/C 1.2, Treiber 417.49, 2048 MiB GPU-Speicher und maximal 512 MiB je Allokation. Kleiner CL1.2-Kernel korrekt; Intel UHD 620 ebenfalls PASS. Der Intel-Speicher ist kein dedizierter NVIDIA-VRAM. Diesen Test nicht wiederholen.
- C++-Buildtools laut Nutzer nicht vorhanden. Am 07.11. ausdrücklich genehmigt: **Microsoft C++ Build Tools samt Windows SDK ausschließlich zum Kompilieren von OpenSfM**. Diese begrenzte Ausnahme zu REQ-ORTHO-03 nicht erneut abfragen. Sie erlaubt keine proprietäre/kostenpflichtige Orthofoto-Engine, keinen Kauf und kein generelles proprietäres Backend.
- Compiler-/SDK-Installation und Start auf dem konkreten Windows-10-Rechner noch offen. Hier wurde kein Installer ausgeführt und keine Kundenaufnahme/SQLite verarbeitet.

## Jetzt: manuelle Installation des genehmigten Buildwerkzeugs

**Neuer Speicherbefund:** C: ca. 5,8 GB frei, E: ca. 291 GB frei; Nutzer noch vor dem Klick auf Installieren. Der Pfad ließ sich im Dialog nicht ändern. Die folgende Belegung auf E: ersetzt die frühere Empfehlung der Standardpfade. Kein erneuter Download nötig, wenn der offizielle Bootstrapper bereits in Downloads liegt.

1. Das aktuelle Installerfenster schließen. Falls der Bootstrapper fehlt, den offiziellen [Microsoft Build Tools 2022 Installer](https://aka.ms/vs/17/release/vs_BuildTools.exe) nach Downloads herunterladen. Der Link bleibt auf **17/2022** begrenzt. Dann den vorhandenen Bootstrapper aus einer neuen PowerShell mit expliziten Speicherorten starten:

```powershell
$setup = Get-ChildItem (Join-Path $env:USERPROFILE 'Downloads') -Filter 'vs_BuildTools*.exe' -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $setup) { throw 'Buildtools-Installer nicht in Downloads gefunden.' }
& $setup --installPath 'E:\Tools\VSBuildTools2022' --path 'cache=E:\Tools\VSCache' --path 'shared=E:\Tools\VSShared' --norestart
```

Die unterstützten Parameter legen Produktverzeichnis, Downloadcache und gemeinsame Komponenten getrennt fest. Die Standardpfade werden nicht durch manuelles Verschieben bestehender Dateien geändert. Es werden keine stillen Installations-/Deinstallations-/Registry-/Junction-Schritte vorgegeben.

2. Im Installer unter **Arbeitslasten** die Auswahl **Desktopentwicklung mit C++ / Desktop development with C++** aktivieren.
3. In den Installationsdetails kontrollieren:
   - **MSVC v143 – VS 2022 C++ x64/x86-Buildtools** (aktueller angebotener v143-Stand).
   - **Windows-SDK** (angebotene empfohlene Version). Ein Paket mit „Windows 11 SDK“ im Namen ist ein Entwicklerpaket und führt kein Betriebssystemupgrade durch. Die offizielle SDK-Dokumentation nennt auch Windows 10 als Host; Zielplattform und konkreter Toolstart bleiben zu prüfen.
4. Unter **Installationsorte** die tatsächlichen Speicherorte und den angezeigten Speicherbedarf je Laufwerk prüfen. Microsoft weist ausdrücklich darauf hin, dass einige Tools/SDK-Teile trotz abweichender Pfade auf dem Systemlaufwerk bleiben. Erst installieren, wenn der verbleibende C:-Bedarf in den freien Platz passt und Reserve bleibt; nicht behaupten, die ganzen Buildtools lägen nun auf E:. Bei weiterhin gesperrten Pfaden, Parameterfehler oder zu hohem C:-Bedarf nur kurze Meldung und C:-Bedarfswert zurückmelden. Vorhandene Visual-Studio-Produkte nicht ungefragt deinstallieren. Die bestehende F:-Python-/Projektumgebung wird nicht umgebaut.
5. Danach eine neue PowerShell öffnen und diesen Komponenten-/Versionsnachweis ausführen:

```powershell
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationVersion
```

Die Versionszeile (vorgesehen `17.…`) zurückmelden. Leere Ausgabe oder kurzer Installerfehler sind ein offener Installationsbefund; keine vollständigen Logs, Benutzerpfade oder Kundendateien übertragen. Das ist eine gezielte Prüfung des nach Installation veränderten Zustands, keine Wiederholung der vorherigen Suche nach bekanntermaßen fehlenden Tools.

Der Komponenten-/Versionsnachweis ist noch kein ausgeführter Compiler-/Linktest. Danach folgen eine getrennte OpenSfM-Umgebung, Paketlösung und tatsächlicher Build-/Werkzeugstart; bis dahin keine Kundendatenrekonstruktion oder Orthofotoqualität behaupten. Die SDK-Header und x64-Linkbibliotheken werden beim konkreten Build benötigt.

### Grenzen der Pfadänderung

Laut [Microsoft-Speicherortanleitung](https://learn.microsoft.com/en-us/visualstudio/install/change-installation-locations?view=vs-2022) lassen sich Produkt-/Cachepfade nur bei der ersten Einrichtung auswählen; gemeinsame Komponenten können durch frühere Visual-Studio-Installationen festgelegt und ausgegraut sein. Die [CLI-Parameterdokumentation](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022) belegt `--installPath`, `--path cache=…` und `--path shared=…`, aber keinen beliebigen Umzug bestehender Installationen. Der neue Startbefehl ist kein Override gesperrter globaler Einstellungen. Der bisherige Nutzerbefund belegt nur, dass die aktuelle Buildtools-Installation noch nicht gestartet wurde; frühere andere VS-Instanzen sind ungeprüft.

Eine Anzeige „Downloadcache nicht behalten“ bzw. `--nocache` vermeidet laut [Microsoft-Cacheanleitung](https://learn.microsoft.com/en-us/visualstudio/install/disable-or-move-the-package-cache?view=vs-2022) nicht den temporären Installationsplatzbedarf. Deshalb keine Lösung allein durch diese Option versprechen. Standardmäßig den vorgesehenen Cache auf E: nutzen; keine eigenmächtige Cachelöschung oder globalen Registry-Eingriffe. Die verbleibenden Systemlaufwerksanforderungen im konkreten Installer prüfen.

## Lizenz- und Windows-10-Grenzen

Die [Microsoft-Lizenzseite](https://visualstudio.microsoft.com/license-terms/vs2022-ga-diagnosticbuildtools/) und das dort verlinkte Lizenzdokument (Update März 2024) wurden gelesen. Die Bedingungen erlauben ohne separate Visual-Studio-Produktlizenz das Kompilieren/Bauen erforderlicher C++-Abhängigkeiten unter OSI-Lizenz; OpenSfM ist eine solche Quellabhängigkeit. Dies ist kein generelles Recht zur beliebigen Entwicklung/Teständerung dieser Abhängigkeit. Compiler/SDK selbst sind proprietär; Build-/SDK-/Weitergabebedingungen bleiben von der BSD-Lizenz von OpenSfM getrennt. Keine automatische Installation oder Weiterverteilung der Microsoft-Tools durch SolarCheck.

Die [aktuelle offizielle 2022-Systemmatrix](https://learn.microsoft.com/en-us/visualstudio/releases/2022/system-requirements) verweist auf OS-Lifecycle und gegebenenfalls ESU. Sie belegt keine pauschale Freigabe jedes Windows-10-Stands. Wenn der normale Installer den vorhandenen Host ablehnt, genaue kurze Meldung auswerten; keine erzwungenen Bypass-Parameter, keinen Wechsel auf Windows 11 oder bezahltes OS-Upgrade verlangen. Der bestandene kleine OpenCL-Kernel bleibt ein eigener Befund.

## Quellenprüfung der erforderlichen Komponenten

- [Offizielle Build-Tools-2022-Komponenten](https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=vs-2022): `Microsoft.VisualStudio.Workload.VCTools`, `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`; Windows-SDK-Komponenten sind aufgeführt. Die geprüfte Tabelle enthält beispielsweise `Microsoft.VisualStudio.Component.Windows11SDK.26100` und die optionalen Windows-10-SDKs.
- [Offizielle Windows-SDK-Dokumentation](https://learn.microsoft.com/en-us/windows/apps/windows-sdk/) nennt Windows 10 als unterstützten SDK-Host. Das ist kein Nachweis der gesamten OpenSfM-/Compilerkette auf dem Nutzerrechner.
- Der HEAD-Aufruf des offiziellen 17/2022-Bootstrappers war erfolgreich; keine Binärdatei hier heruntergeladen oder gestartet.
- **Korrektur zu upstream:** `vs2022_win-64` liefert nicht bereits einen vollständigen MSVC-Compiler. Die [Metadaten des upstream gelockten Pakets](https://api.anaconda.org/package/anaconda/vs2022_win-64) nennen Aktivierung/Versionsprüfung, 18693 Bytes und nur `vswhere` als Abhängigkeit; [conda-forge](https://api.anaconda.org/package/conda-forge/vs2022_win-64) bietet ebenfalls diese kleine Aktivierungshilfe. Die [upstream Buildanleitung](https://github.com/OpenSfM/OpenSfM/blob/8b6b77efddebf4429044d3206c7dc21c4e767e08/doc/building.md) insoweit nicht blind übernehmen.
- Der originale Windows-Lock mischt 72 conda-forge- und 100 anaconda-Pakete; `conda.yml` nennt ausdrücklich `anaconda::metis`. Miniforge als Basis ändert diese Quellen nicht. Ein ausschließlich aus conda-forge stammender Ersatz ist noch nicht gelöst/gebaut/geprüft.
- CPU-Ceres 2.2 ist in den conda-forge-Windows-Metadaten verfügbar. Spätere Rezeptur muss CUDA-Varianten vermeiden und BLAS-/Paketvarianten sowie Lizenzen konkret prüfen. Paketverfügbarkeit ist keine erfolgreiche Umgebung.

## Gemeinsamer Code für Offline und Online

Nutzer bestätigt die gemeinsame Entwicklung: derselbe Python-Fachkern für OpenSfM-Aufrufkette, Raster-/GeoTIFF-Prüfung, PV-Modul-IDs, Thermal-Zuordnung und Berichte. Desktop und Weboberfläche sowie lokaler/Server-Jobstart und Betriebssystem-Buildskripte sind Adapter. Windows-Laufwerksbuchstaben, GUI-Abhängigkeiten und Compilerpfade gehören nicht in den Fachkern. Für beide Plattformen dieselbe OpenSfM-Quellversion und nachvollziehbare Konfiguration qualifizieren; Linux-Server und Windows-10-Nutzerlauf gesondert testen.

Die genehmigten Microsoft-Werkzeuge betreffen den Windows-Build, binden den gemeinsamen Fachcode nicht an einen Windows-Server und sind keine Anweisung zu jetzigen Kundenbild-Uploads. Offline zuerst; Online später. Nach erfolgreichem Werkzeugbuild vollständige dokumentierte GeoTIFF-Stufen ohne Kundenbilder prüfen, dann bewusster lokaler RGB-Serienlauf, danach passendes Thermal/Werteerhalt und vorhandene PV-/Review-/Berichtskette. Keine eigene Photogrammetrie oder ODM/WebODM/ODX-Integration.

## Historische Miniforge-Quelle (bereits eingerichtet)

Offizielle Miniforge3 26.9.4-2 Windows-x86_64-Quelle: [Release](https://github.com/conda-forge/miniforge/releases/tag/26.9.4-2), [Lizenz](https://github.com/conda-forge/miniforge/blob/26.9.4-2/LICENSE). Installer-Code BSD-3-Clause, mitgelieferte Pakete mit eigenen OSI-Lizenzen. Release-Digest und offizielle Prüfsummendatei abgeglichen: `9d83983669bc5d3b5dd4c631454bf953c3caf4ac78b9c9ada9971e5b021d83c3`, 158341784 Bytes laut Release. Kein Installer hier heruntergeladen/gestartet. Kein erneuter Installationsauftrag; F:-Python, SQLite, Originale und gestoppte Jobs erhalten.
