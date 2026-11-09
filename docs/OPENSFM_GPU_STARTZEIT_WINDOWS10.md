# OpenSfM-GPU-Probe: Importzeit und native Laufzeit getrennt begrenzen

**OPEN-SFM-NVIDIA-01 abgeschlossen:** Nutzer bestätigt NVIDIA582.78 installiert und Rechner neu gestartet. Treiber, Compiler und OpenSfM nicht nochmals installieren.

**Neuer Nutzerbefund09.11.2026:** Die bisherige Probe endet mit inventory_failed/timeout, last_stage official_cli_imports. Das ist ein anderer Befund als der vorherige0xC0000005-Absturz beim Prozessende. Die expliziten Geräteabfragen und der Matcher wurden noch nicht erreicht. Daraus weder behobenen Treiberfehler noch neue GPU-Untauglichkeit ableiten. Die Visual-Studio-Aktivierung davor ist kein Compilerfehler.

Der bisherige Adapter begrenzt einen ganzen Worker einschließlich aller Python-Importe auf30 s. Upstreams opensfm.commands lädt die gesamte Befehlsregistry samt Statistik-/Berichts-/Dense-Abhängigkeiten. Ein langsamer Import kann damit vor jeder GPU-Prüfung abgebrochen werden. Ob der aktuelle Import langsam oder blockiert ist, bleibt offen; kein belegter Fontcache-/Treibergrund.

## Gezielte Adapterkorrektur OPEN-SFM-START-01

Mit --phase-timeouts gelten pro Worker zwei getrennte Zeitfenster: **bis120 s für Loader/Importe**, danach **30 s für native Geräteabfragen beziehungsweise Matching samt Prozessende**. Eine feste Bereitschaftsmarke nach vollständig geladenen Modulen wechselt einmal zur nativen Phase. Sie wird zusätzlich exklusiv in eine winzige lokale Datei in einem eigenen neuen gpu-start-Ordner neben dem Prüfskript geschrieben; nach dem Worker wird nur dieser eigene Ordner entfernt. Dies ist unter Windows erforderlich, weil communicate-Zeitüberschreitungen dort keine laufende Standardausgabe liefern. Keine privaten Dateien lesen/überschreiben. Wiederholte Marker verlängern sie nicht. Kein zusätzlicher Warmup-Worker und keine neue Loader-/Importreihenfolge. Bei Timeout meldet der Bericht timeout_phase/limit_seconds/last_stage; rohe Ausgabe bleibt verborgen. Teil-JSON oder fertiger Matcher vor einem fehlerhaften Prozessende wird weiterhin nicht als PASS akzeptiert.

Unveränderte OpenSfM-Engine, gleiche System32-/offizielle CLI-Startart,64 künstliche Deskriptoren, keine Fotos/SQLite. Die Probe startet Matching nur nach sauber beendetem Inventar. Sie beendet nur ihren eigenen Worker bei Timeout/Abbruch. Keine Treiber-/Paketinstallation und kein Nachtlauf. Der alte Startmodus bleibt für historische Pins erhalten; jetzt nur den neuen expliziten Phasenmodus verwenden.

## Vollständiger PowerShell-Startblock

Die aktualisierte Probe wird mit fester Quellversion und SHA256 als **neue Datei** gespeichert. Die alte GPU-/Stackprobe wird nicht überschrieben. Keine Compiler-/Treiber-/Engineinstallation. Genau diesen Block einmal in normaler PowerShell ausführen; die Begrenzungen stehen auch im abschließenden JSON unter time_limits_seconds.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $wurzel = 'E:\SolarCheck-OpenSfM'
    $pruefung = Join-Path $wurzel 'MCM_SolarCheck_OPENSFM_GPU_START_PRUEFUNG.py'
    $quelle = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/c4a4d398b015a69d0bdca772b497cdfad0c1be1f/scripts/MCM_SolarCheck_OPENSFM_GPU_PRUEFUNG.py'
    Invoke-WebRequest -UseBasicParsing -Uri $quelle -OutFile $pruefung
    if ((Get-FileHash -LiteralPath $pruefung -Algorithm SHA256).Hash -ne '1bd4041bf460830bef1c070a0801de2d09bfa61097a6325812818d5146ac1459') {
        throw 'Pruefsumme der neuen Startprobe stimmt nicht; keine Ausfuehrung.'
    }
    New-Item -ItemType Directory -Path "$wurzel\tmp","$wurzel\matplotlib" -Force | Out-Null
    $neu = @{ TEMP="$wurzel\tmp"; TMP="$wurzel\tmp"; MPLCONFIGDIR="$wurzel\matplotlib"; PROJ_NETWORK='OFF' }
    $alt = @{}
    foreach ($key in $neu.Keys) { $alt[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
    try {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $neu[$key], 'Process') }
        & 'E:\Tools\Miniforge3\Scripts\conda.exe' run --no-capture-output --prefix "$wurzel\env" python -I $pruefung --system-opencl --cli-imports --phase-timeouts
    } finally {
        foreach ($key in $neu.Keys) { [Environment]::SetEnvironmentVariable($key, $alt[$key], 'Process') }
    }
}
```

**Nur den letzten JSON-Block melden.** Bei erneutem Timeout stehen dort nun timeout_phase (startup/native), limit_seconds und last_stage. Keine weiteren Zeitverlängerungen oder Startvarianten versuchen. Ein Importtimeout ist keine GPU-Qualitätsaussage. Ein neuer0xC0000005-Exit bleibt ein echter Fehler; keine weitere Stackdiagnose auf Verdacht. dataset/dense_reconstruction bleiben not_tested. Erst ein sauberer Inventarexit und korrekte64 Identitätspaare mit sauberem Matcherexit zählen als kleiner GPU-Funktionstest.

Lokal39 GPU-/Zeitsteuerungstests bestanden, einschließlich tatsächlicher isolierter Python-Prozesse. Geprüft: längere erfolgreiche Importe, getrennte Deadlines, keine Verlängerung durch wiederholte/unbekannte Marker, echte Pipe-Retries, eigener Startup-/Native-Timeout, CLI-Weitergabe, Windows-Pufferverhalten, eigene exklusive Bereitschaftsdatei samt Bereinigung und kein PASS nach Crash. Quellec4a4d398: [Windows-CI42694877874](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/42694877874) hat die tatsächlichen isolierten Prozess-/Pipe-/Dateisignal-/Startup-/Native-Timeoutfälle auf Python3.11 und3.12 bestanden. Die erste Adapterfassung scheiterte dort an fehlender partieller Standardausgabe; die korrigierte Fassung verwendet deshalb die eigene Bereitschaftsdatei. Windows Server2022 beweist keine reale GPU-/Windows10-Funktion; vollständige Workflows/neuen Dokumentations-HEAD separat prüfen. Nutzerlauf mit korrigiertem Adapter bleibt offen. Dataset/Dense/Orthofotos bleiben ungetestet; nach sauberem kleinem GPU-Test erst den begrenzten lokalen RGB-Weg mit der vorhandenen GeoTIFF-/PV-Kette verbinden.

[Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md). Keine neue Photogrammetrie-Engine und kein Merge nach main.
