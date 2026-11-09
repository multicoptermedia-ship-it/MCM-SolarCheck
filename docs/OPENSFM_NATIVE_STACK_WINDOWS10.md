# Native OpenSfM-Absturz-Aufrufkette unter Windows 10

**OPEN-SFM-GPU-03 abgeschlossen09.11.2026:** Der reguläre CLI-Einstieg mit bestehendem System32-OpenCL erkennt ein Gerät/eine GPU und schreibt completed/worker_complete. Danach beendet sich der Worker mit0xC0000005. Kein Matching gestartet, keine GPU-Freigabe. Windows meldet ntdll.dll/Offset24785, ohne konkrete Ursache zu beweisen. Weitere Import-/Loader-/Treibervarianten sind kein nächster Schritt. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

**OPEN-SFM-STACK-01:** Ein kleiner Diagnoseadapter verwendet die vorhandenen Microsoft-Buildwerkzeuge und die Standard-Windows-APIs CreateProcess/WaitForDebugEvent/StackWalk64. Er kompiliert nur eigene neue Dateien in einem neuen stack-Ordner auf E:. Kein Installer oder Engine-Neubau. Nur der festgelegte Inventarworker wird gestartet, mit demselben --system-opencl/--cli-imports wie bisher. Keine Verbindung zu einem laufenden Fremdprozess, keine Matching-/Bild-/DB-Verarbeitung und keine Engineänderung.

Der Adapter hält den Prozess bei einer unbehandelten Ausnahme kurz an, liest mit Microsofts x64-Unwinder höchstens32 Stackframes und lässt die Ausnahme unbehandelt weiterlaufen. Der ursprüngliche Exitcode bleibt erhalten. Die Ausgabe enthält nur DLL-/Modulbasenamen und relative Offsets, keine absoluten Speicheradressen oder Pfade. Es wird kein Speicherabbild erstellt. Kindausgabe geht nach NUL, rohe Engineausgabe wird nicht gespeichert. Compilerlogs bleiben im eigenen neuen lokalen Diagnoseordner.

Symbolsuche: expliziter eigener leerer Ordner, Umgebungs-Symbolpfade und eingebettete PDB-Verweise ignoriert; kein Symbolserver/Download konfiguriert. Es werden nur lokale PE-/x64-Unwindinformationen verwendet. TEMP/TMP/MPLCONFIGDIR liegen im neuen E:-Ordner, PROJ-Netz aus. Inventarprozess30 s begrenzt, äußerer Diagnoseprozess40 s. Bei Timeout endet nur der eigene Prozess. Ein Debugger kann das Absturzverhalten beeinflussen; clean_exit unter Debugger wäre kein Beweis einer Reparatur.

Vor OpenSfM prüft der Adapter sich mit zwei eigenen synthetischen Prozessen: kontrollierter unbehandelter AV und normaler Exit. Erst bei erfolgreicher Stackaufnahme mit unverändertem AV-Exit und sauberem Vergleichsexit startet er den bekannten Inventarworker. diagnostic_complete bedeutet allein Diagnose abgeschlossen, accepted_as_gpu_success bleibt false. Teilweise/fehlende Frames sind möglich, insbesondere bei bereits entladenen Modulen; daraus keine konkrete Ursache erfinden.

## Startblock

Wird nach tatsächlicher Windows-CI-Abnahme von Compile/Debug/Stackaufnahme/sauberem Exit/eigenem Timeout mit fester Quellversion und SHA256 ergänzt. Bis dahin diesen neuen Adapter nicht ausführen. Compiler/SDK/Umgebung/Quellbau sind bereits abgeschlossen und werden nicht erneut installiert oder allgemein getestet.

Lokale Adapter-/Protokollprüfung:37 Tests bestanden, ein nativer Windows-Test unter Linux übersprungen. Die Windows-CI muss den Helper tatsächlich kompilieren, einen eigenen AV debuggen, Modul/Offsets auslesen, Exit0xC0000005 erhalten und einen eigenen wartenden Kindprozess beenden. Keine echte GPU und kein OpenSfM-Datensatz in CI; der Nutzerbefund der realen Aufrufkette bleibt danach offen.
