# OpenSfM unter Windows 10 – Buildwerkzeuge vorbereiten

**OPEN-SFM-SETUP-01 · Nutzerfreigabe 07.11.2026.** [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md) · [OpenSfM-Quellenprüfung](OPENSFM_PRUEFUNG_2026-11-07.md).

## Aktueller Stand – 08.11.2026

Der Nutzer hat den Rechner aufgeräumt und meldet **28 GB freien Speicher auf C:**. Die Speicherklärung ist beendet. Keine weiteren WinDirStat-/AppData-/Arduino-/Hiber-Abfragen oder Bereinigungsaufträge. Welche einzelnen Schritte er durchgeführt hat, ist nicht angegeben; keinen konkreten staging-Umzug als bestätigt melden. QGIS samt Erweiterungen, beide Profile, bestehende Arduino-Nutzung und SolarCheck-Projekt erhalten.

- **MSVC-SDK-01 beim Nutzer bestanden:** status/cpp17_windows_sdk_x64 passed, vs_version17.14.37827.9. Tatsächliche C++17-/Windows-SDK-/x64-Compile/Link/Run-Prüfung unter Windows10 abgeschlossen. Build Tools2022 17.14.44 laut Installerbild. Produkt und Downloadcache auf E:, gemeinsame Komponenten auf C:. Keine Neuinstallation/erneute Logsammlung.
- Miniforge **conda26.9.4** erreichbar, OpenCL-Kerntest auf MX250/Intel bestanden; nicht wiederholen. Diese Befunde beweisen noch keinen OpenSfM-Build.
- Microsoft-C++-Buildtools/SDK ausschließlich für den OpenSfM-Build freigegeben (REQ-ORTHO-03A); nicht erneut bestätigen lassen. Windows10 bleibt Zielplattform, vorhandenes F:-Python und SQLite werden erhalten.
- Neue Builddateien und Paket-Caches weiterhin auf E: vorsehen. 28 GB sind ein aktueller Nutzerbefund, keine allgemeine Garantie für den Speicherbedarf aller noch ungelösten Pakete.

## Nächster Schritt: OpenSfM-Quellbau qualifizieren

**MSVC-SDK-01 und OPEN-SFM-ENV-01 beim Nutzer abgeschlossen.** Die getrennte Umgebung E:\SolarCheck-OpenSfM\env wurde am08.11.2026 mit Python3.10.22 erfolgreich geprüft:22 isolierte Bibliotheksimporte, GeoTIFF-Treiber verfügbar, PROJ-Netz aus. Nicht neu anlegen oder entfernen. [Abgeschlossener Umgebungsweg](OPENSFM_UMGEBUNG_WINDOWS10.md). F:-Python/SQLite bleiben erhalten.

OpenSfM-v1.1-Quellbau aus8b6b77efddebf4429044d3206c7dc21c4e767e08 ist im Windows-Lauf42517970232 (Quelle d8e6eb3c) gegen genau diesen Lock bestanden: neun native Module, OpenCL mitkompiliert, Konstantentest/CLI-Registry PASS. Jetzt [konkreten Nutzerbaublock](OPENSFM_QUELLBAU_WINDOWS10.md) verwenden. Reale Windows10-Build-JSON-Ausgabe und GPU-/RGB-/Thermalnachweis bleiben offen. Keine erneute Paketauflösung/Compiler-/SDK-/OpenCL-Inventur. Bestehende GeoTIFF-/PV-Kette erhalten.

## Abgeschlossen: Compiler-/SDK-/x64-Test – nicht erneut ausführen

[Prüfdatei MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py](../scripts/MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py), festgelegte Quelle **d6fa78cb751a6443ff742b91b035852ef8c45c67**. Dieser Block in einer normalen PowerShell lädt nur die kleine SolarCheck-Quelldatei nach E: und startet sie mit dem vorhandenen F:-Python. Ein Downloadfehler beendet den Block vor dem Start einer alten Datei:

```powershell
& {
    $zielOrdner = 'E:\Tools\SolarCheck-Checks'
    New-Item -ItemType Directory -Path $zielOrdner -Force -ErrorAction Stop | Out-Null
    $pruefung = Join-Path $zielOrdner 'MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/d6fa78cb751a6443ff742b91b035852ef8c45c67/scripts/MCM_SolarCheck_BUILDTOOLS_PRUEFUNG.py' -OutFile $pruefung -ErrorAction Stop
    & 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' $pruefung
}
```

Quell-URL erfolgreich gelesen und bytegenau mit der Repositorydatei verglichen:8038 Bytes, SHA256 `6e2487b806740f9c7c5155214b2049650d36e614508cd334cbaef910e7ac4855`. Kein Installer oder Paketdownload durch die Prüfdatei selbst; der obige manuelle Startblock benötigt Internet nur zum Laden ihres Quellcodes.


Die Prüfdatei verwendet nur die Python-Standardbibliothek und die vorhandenen VS2022-C++-Werkzeuge. Sie startet keinen Installer, lädt keine Pakete herunter und liest keine Projekt-/Fotoordner. Registrierte vollständige VS2022-Installation wird über das vorhandene vswhere gefunden. Ausschließlich eigene neue Dateien unter **E:\Tools\SolarCheck-BuildCheck\probe-…**: synthetisches C++17-Programm, Batchdatei, Objekt/EXE, lokale Protokolle und Temp-Unterordner. Kein C:-Fallback und keine Bereinigung/Überschreibung alter Läufe. TEMP/TMP nur im Testkindprozess auf den eigenen E:-Unterordner gesetzt, keine dauerhaften Umgebungs-/Registry-/PowerShell-Einstellungen.

Der Test kompiliert Windows-SDK-Header, linkt eine Kernel32-Funktion und C++-Standardbibliothek, prüft den x64-PE-Typ und startet die eigene kleine EXE mit fest erwarteter Ausgabe. Nur ein Build-Exitcode0 reicht nicht für PASS. Installer-/OpenSfM-Start und Fotos sind nicht Teil der Prüfung. VS-Abfrage maximal15 Sekunden, Compiler-/Testlauf45 Sekunden; bei Überschreitung nur eigenen Prozessbaum beenden. Rohprotokolle bleiben lokal, zurückmelden nur die kurze JSON-Ausgabe; sie enthält keine Benutzer-/Kundenpfade. Kompilerfehler werden als feste Codes wie C1083/LNK1104 ausgegeben. Kein ungeprüfter Treiber-/SDK-/Installer-Neustart aus einem Fehlerstatus.

Der feste E:-Standardpfad verwendet nur einfache ASCII-Zeichen. `output_path_unsupported` oder `setup_path_unsupported` bedeutet, dass ein Pfad wegen Zeichen wie &/%/! nicht an die Microsoft-Batchaktivierung übergeben wird; dort wurde in nativer CI ein Fehler der VsDevCmd-Initialisierung beobachtet. Die Probe startet in diesem Fall nicht weiter und schreibt bei ungeeignetem Ausgabeordner keine Dateien. Keine Pfad-/Registry-Umgehung; kurzen Status einordnen. Auch Leerzeichen/Klammern im temporären Prüfordner werden vorab abgewiesen: native CI zeigte einen Parserfehler des Microsoft-Startskripts bei diesem TEMP-Pfad. Der feste E:-Standardpfad passt dazu; normale Leerzeichen/Klammern im Visual-Studio-Installationspfad bleiben zulässig.

`status: passed` mit `cpp17_windows_sdk_x64: passed` bestätigt diese kleine Toolchain-Probe auf dem konkreten Rechner. `opensfm: not_tested` bleibt ausdrücklich erhalten. Erst danach getrennte OpenSfM-Umgebung/Paketlösung, echter Build und Werkzeugstart; noch keine Kundenbilder oder Orthofotoqualität. Der upstream Windows-Lock/pure-conda-forge-Ersatz ist weiterhin ungeklärt, keine komplette Einrichtung behaupten.

**Prüfstatus Quelle d6fa78cb:** Lokal68 zielgerichtete Tests bestanden/vier native Windows-Skips. Der tatsächliche Compiler-/SDK-/x64-Lauf ist auf Windows2022/Python3.11 und3.12 im [Windows-CI-Lauf](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42508265683) bestanden. Alle drei vollständigen Workflows am Quell-HEAD d6fa78cb sind erfolgreich (Windows42508265683, Linux42508265618/42508261362). Ein neuer Dokumentations-HEAD wird dadurch nicht automatisch grün. Nutzer08.11. meldet inzwischen denselben PASS unter Windows10 mit vs_version17.14.37827.9. Diese Qualifikation ist abgeschlossen; nächster Schritt Engine-Umgebung/Paketlösung/Build. Keine erneute Compiler-/Installer-/OpenCL-Schleife ohne Fehlerbefund.


## Abgeschlossene Speicherklärung – Historie

Zuvor C206,4 GB gesamt/203,8 belegt/2,6 frei; WinDirStat zeigte Users93,99 GiB als größten Bereich. AppData/Local/Arduino15, staging/packages ungefähr gleich groß. Manuelle Archivierung nur von staging auf E: war vorbereitet; packages/Arduino/QGIS/Plugins und Projekte sollten erhalten bleiben. Nutzer meldet08.11. nur das Ergebnis28 GB frei. Kein weiterer Verschiebe-/Löschauftrag. Offizielle [Arduino-CLI-Doku](https://docs.arduino.cc/arduino-cli/configuration/) unterscheidet Boarddaten und staging-Downloadarchive. Früherer WinDirStat-Portable-Scan ist erledigt, Tool nicht in SolarCheck integrieren. Hiberdatei war nicht vorhanden; keine powercfg-/Auslagerungsdatei-/Profil-/Registry-Eingriffe.

## Historie: korrigierter interaktiver Start – jetzt nicht erneut ausführen

**Nutzerbericht erhalten:** Älterer Installer-Lauf mit Exitcode 87, neuerer Installer-Lauf und Setup-Logs mit 0; keine Hex-Fehler. Die Nullcodes sind kein Nachweis installierter C++-Komponenten. Die reine Logprüfung ist abgeschlossen und wird nicht erneut angefordert.

**Fehler im bisherigen eigenen Befehl:** `--norestart` war im interaktiven Aufruf enthalten. Laut [Microsoft-Parameterdokumentation](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022) muss dieser Schalter mit `--quiet` oder `--passive` kombiniert werden. Der bisherige Aufruf verletzte diesen Vertrag und ist zurückgezogen. Das passt zu 87 („Ungültiger Parameter“), beweist aber nicht, welches Argument im konkreten älteren Lauf beanstandet wurde. Nicht durch stillen/passiven Betrieb ersetzen: Die C:-Platzprüfung muss sichtbar bleiben.

Vor diesem **gezielt korrigierten** Start noch offene Installerfenster schließen, sofern darin keine Installation läuft. Der folgende Block lädt ausdrücklich den offiziellen 17/2022-Bootstrapper nach E:; er wählt keine beliebige neueste Datei aus Downloads. Produkt-/Cache-/Shared-Verzeichnisse werden dabei auf E: angefordert, ein verbleibender C:-Bedarf besteht weiterhin.

<!-- tested-buildtools-interactive-start -->
```powershell
& {
    New-Item -ItemType Directory -Path 'E:\Tools\Installers' -Force -ErrorAction Stop | Out-Null
    $setup = 'E:\Tools\Installers\vs_BuildTools_2022.exe'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' -OutFile $setup -ErrorAction Stop
    Write-Host 'Installer wird gestartet. Bitte im Installer den Abschluss abwarten.'
    $argumente = @(
        '--installPath', 'E:\Tools\VSBuildTools2022',
        '--path', 'cache=E:\Tools\VSCache',
        '--path', 'shared=E:\Tools\VSShared',
        '--wait'
    )
    $prozess = Start-Process -FilePath $setup -ArgumentList $argumente -Wait -PassThru -ErrorAction Stop
    Write-Host "Installer-Exitcode: $($prozess.ExitCode)"
}
```

Im sichtbaren Installer **Desktopentwicklung mit C++**, **MSVC v143 x64/x86** und **Windows-SDK** auswählen; tatsächlichen Restbedarf auf C: vor Installieren prüfen (bisher ca. 5,8 GB frei, Reserve nötig). Bei gesperrten bestehenden Shared-/Cachepfaden oder zu hohem Restbedarf Meldung auswerten; keine Umgehungs-/Cleanup-Schritte.

PowerShell wartet bewusst, solange der gestartete Installer läuft. Der angezeigte `Installer-Exitcode` kommt erst nach dessen Ende. `--wait` ist hier zulässig, weil ein Bootstrapper gestartet wird, nicht `setup.exe`; `Start-Process -Wait -PassThru` hält zudem den Prozess/Exitcode fest. Die Ausgabe sagt allein noch nicht, dass C++ vollständig vorhanden ist. Nach Ergebnis den konkreten Produkt-/Komponentenstatus prüfen; nicht erneut allgemein auf eine fehlende Ausgabe schließen.

Native Windows-Tests führen genau diesen Dokumentationsblock mit simuliertem Download/Installer aus, prüfen den Microsoft-Parametervertrag, sichtbaren Modus, E:-Ziele, Warten/Exitcode und Abbruch vor Start bei Downloadfehler. Keine echten Installer oder Netzverbindungen in den Tests. Der tatsächliche korrigierte Nutzerlauf und Windows-10-/Compilernachweis stehen aus.

## Abgeschlossener Schritt: vorhandene Setup-Protokolle auswerten

**Neuer Nutzerbefund:** Die Installation war angehalten. Ein erneuter Start des bisherigen E:-Befehls öffnet und schließt das Fenster rasch; laut Nutzer zeigt der Installer kein Produkt. Die eingeschränkte isComplete-Abfrage und später die breite Abfrage lieferten keine verwertbare Ausgabe. Daraus weder erfolgreiche Installation noch einen bestimmten Fehler ableiten. Mit „diese Version“ war kein neuer Versionsnachweis gemeint, sondern der wiederholte Start desselben Befehls.

Der abgeschlossene Diagnoseschritt verwendete [MCM_SolarCheck_BUILDTOOLS_LOGCHECK.py](../scripts/MCM_SolarCheck_BUILDTOOLS_LOGCHECK.py). Historischer Aufruf der bereits ausgeführten Prüfdatei (nicht wiederholen):

```powershell
$pruefung = Join-Path $env:USERPROFILE 'Downloads\MCM_SolarCheck_BUILDTOOLS_LOGCHECK.py'
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' $pruefung
```

Sie druckt eine Startzeile und einen JSON-Bericht, auch wenn keine Protokolle gefunden werden. Nur die Ausgabe zurückmelden; keine vollständigen Protokolle übertragen. Sie startet/ändert den Installer nicht, schreibt/löscht keine Dateien und ändert keine Registry. Die gezielte Suche beschränkt sich auf vorhandene Windows-Temp-Verzeichnisse und `dd_bootstrapper_*.log`, `dd_installer_*.log`, `dd_setup_*.log` der letzten 24 Stunden, maximal zwei neueste Dateien je Typ. Symlinks werden übersprungen, höchstens 256 KiB vom Ende gelesen (plus Kodierungsgrenze). UTF-8/-16 werden unterstützt. Ausgegeben werden nur Protokolltyp, Alter, Hex-/Exitcodes und Zähler fehlender/unlesbarer Codes; keine Rohtexte, Dateinamen, Pfade, Rechner-/Benutzernamen, Download-URLs oder Koordinaten.

Codes können zu verschiedenen Phasen/Versuchen gehören; Alter und Typ zusammen lesen. `no_recent_setup_logs` belegt nicht, dass keine Installation vorhanden ist. Nullcodes oder ein erfolgreicher Bootstrapper sind kein Compiler-/C++-Komponentennachweis. Erst tatsächliche Codes einordnen, dann genau eine passende Korrektur ableiten. Kein weiterer unveränderter Start, keine Cleanup-/Deinstallations-/Registry-Aktionen aus diesen bisherigen Befunden.

Microsoft dokumentiert [Bootstrapper-Exitcodes und --wait](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022): `--wait` gilt nur für den Bootstrapper, nicht `setup.exe`; es wäre für einen späteren beobachteten Start relevant. Beispiele sind 5003 (Installerdownload), 5005 (Argumentverarbeitung), 5007/8010 (Voraussetzungen/OS) oder 8004 (Zielverzeichnis). Keine dieser Ursachen ist bisher belegt. Ein verändertes Fensterverhalten allein genügt nicht. Der frühere Downloads-Selektor „neueste vs_BuildTools*.exe“ belegt außerdem nicht die tatsächlich verwendete Produktgeneration/Quelle; bei späterem neuem Start diese ausdrücklich qualifizieren.

Technische Tests verwenden nur synthetische Logs, einschließlich künstlicher Pfade/Koordinaten und UTF-16-Tails. Sie prüfen gezielte Suche, Alter/Größenlimit, kein Rohtext-/Pfadexport, explizite leere/unlesbare Ergebnisse und Abhängigkeit nur von der Standardbibliothek. Keine echten Nutzerlogs oder Installer in CI. Der Nutzercheck ist ausgeführt; Codes87/0 erhalten. Das im konkreten älteren Lauf beanstandete Argument bleibt unbelegt, der eigene Parametervertragsfehler ist separat bestätigt.

## Historischer Installationsversuch auf E: – aktuell nicht wiederholen

**Neuer Speicherbefund:** C: ca. 5,8 GB frei, E: ca. 291 GB frei; Nutzer noch vor dem Klick auf Installieren. Der Pfad ließ sich im Dialog nicht ändern. Die folgende Belegung auf E: ersetzt die frühere Empfehlung der Standardpfade. Kein erneuter Download nötig, wenn der offizielle Bootstrapper bereits in Downloads liegt.

1. Das aktuelle Installerfenster schließen. Falls der Bootstrapper fehlt, den offiziellen [Microsoft Build Tools 2022 Installer](https://aka.ms/vs/17/release/vs_BuildTools.exe) nach Downloads herunterladen. Der Link bleibt auf **17/2022** begrenzt. Dann den vorhandenen Bootstrapper aus einer neuen PowerShell mit expliziten Speicherorten starten:

Der frühere Downloads-Selektor und interaktive Aufruf mit `--norestart` wurden wegen des bestätigten Parametervertragsfehlers zurückgezogen. Den oben angegebenen korrigierten Block verwenden.

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
