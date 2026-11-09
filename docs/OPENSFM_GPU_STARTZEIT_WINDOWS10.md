# OpenSfM-GPU-Probe: Importzeit und native Laufzeit getrennt begrenzen

**OPEN-SFM-NVIDIA-01 abgeschlossen:** Nutzer bestätigt NVIDIA582.78 installiert und Rechner neu gestartet. Treiber, Compiler und OpenSfM nicht nochmals installieren.

**Neuer Nutzerbefund09.11.2026:** Die bisherige Probe endet mit inventory_failed/timeout, last_stage official_cli_imports. Das ist ein anderer Befund als der vorherige0xC0000005-Absturz beim Prozessende. Die expliziten Geräteabfragen und der Matcher wurden noch nicht erreicht. Daraus weder behobenen Treiberfehler noch neue GPU-Untauglichkeit ableiten. Die Visual-Studio-Aktivierung davor ist kein Compilerfehler.

Der bisherige Adapter begrenzt einen ganzen Worker einschließlich aller Python-Importe auf30 s. Upstreams opensfm.commands lädt die gesamte Befehlsregistry samt Statistik-/Berichts-/Dense-Abhängigkeiten. Ein langsamer Import kann damit vor jeder GPU-Prüfung abgebrochen werden. Ob der aktuelle Import langsam oder blockiert ist, bleibt offen; kein belegter Fontcache-/Treibergrund.

## Gezielte Adapterkorrektur OPEN-SFM-START-01

Mit --phase-timeouts gelten pro Worker zwei getrennte Zeitfenster: **bis120 s für Loader/Importe**, danach **30 s für native Geräteabfragen beziehungsweise Matching samt Prozessende**. Eine feste Bereitschaftsmarke nach vollständig geladenen Modulen wechselt einmal zur nativen Phase. Sie wird zusätzlich exklusiv in eine winzige lokale Datei in einem eigenen neuen gpu-start-Ordner neben dem Prüfskript geschrieben; nach dem Worker wird nur dieser eigene Ordner entfernt. Dies ist unter Windows erforderlich, weil communicate-Zeitüberschreitungen dort keine laufende Standardausgabe liefern. Keine privaten Dateien lesen/überschreiben. Wiederholte Marker verlängern sie nicht. Kein zusätzlicher Warmup-Worker und keine neue Loader-/Importreihenfolge. Bei Timeout meldet der Bericht timeout_phase/limit_seconds/last_stage; rohe Ausgabe bleibt verborgen. Teil-JSON oder fertiger Matcher vor einem fehlerhaften Prozessende wird weiterhin nicht als PASS akzeptiert.

Unveränderte OpenSfM-Engine, gleiche System32-/offizielle CLI-Startart,64 künstliche Deskriptoren, keine Fotos/SQLite. Die Probe startet Matching nur nach sauber beendetem Inventar. Sie beendet nur ihren eigenen Worker bei Timeout/Abbruch. Keine Treiber-/Paketinstallation und kein Nachtlauf. Der alte Startmodus bleibt für historische Pins erhalten; jetzt nur den neuen expliziten Phasenmodus verwenden.

## Startblock

Nach tatsächlicher Windows-Abnahme der Prozess-/Zeitgrenzen wird hier der vollständige Block mit fester Quellversion und SHA256 ergänzt. Neue Datei erhält den Namen MCM_SolarCheck_OPENSFM_GPU_START_PRUEFUNG.py; die frühere GPU-/Stackprüfdatei bleibt erhalten. Keine Neuinstallation oder weitere Geräte-/Loaderauswahl.

Lokal39 GPU-/Zeitsteuerungstests bestanden, einschließlich tatsächlicher isolierter Python-Prozesse. Geprüft: längere erfolgreiche Importe, getrennte Deadlines, keine Verlängerung durch wiederholte/unbekannte Marker, echte Pipe-Retries, eigener Startup-/Native-Timeout, CLI-Weitergabe, Windows-Pufferverhalten, eigene exklusive Bereitschaftsdatei samt Bereinigung und kein PASS nach Crash. Echte Windows-Prozesssteuerung noch offen. Dataset/Dense/Orthofotos bleiben ungetestet; nach sauberem kleinem GPU-Test erst den begrenzten lokalen RGB-Weg mit der vorhandenen GeoTIFF-/PV-Kette verbinden.

[Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md). Keine neue Photogrammetrie-Engine und kein Merge nach main.
