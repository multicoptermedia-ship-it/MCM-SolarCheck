# MicMac separat auf dem Windows-10-Auswerterechner einrichten

Nutzerbestätigung 01.11.2026: **Windows 10 bleibt**, kein Wechsel auf Windows 11. GUI, Projektanmeldung und Import wurden dort bereits getestet. **Aktualisierung: Nutzer meldet `E:\Tools\MicMac\bin\mm3d.exe`** (Schreibabstände normalisiert). Die frühere Angabe „noch nicht installiert“ ist überholt. Jetzt den lokalen Start prüfen; Version/Helfer/Rechenlauf sind noch nicht bestätigt. Nicht erneut Betriebssystem oder Installationspfad erfragen.

## Jetzt ausführen: Starttest am gemeldeten Pfad

PowerShell auf dem Windows-10-Auswerterechner öffnen und ohne Bildargumente starten:

```powershell
& 'E:\Tools\MicMac\bin\mm3d.exe'
```

Erwartet wird eine Hilfe-/Kommandoliste. Rückmeldung: erscheint diese Liste, oder welcher genaue Fehlertext wird ausgegeben? Noch keine Fotos oder GPS-Daten für diesen Test verwenden. Cloud-Codex kann die lokale E:-Festplatte nicht prüfen. Die folgenden Einrichtungsschritte sind Referenz und müssen bei vorhandener Installation nicht wiederholt werden.

## Bezugsquelle und Installationsgrenze

Die offizielle [MicMac-Version v1.2.0](https://github.com/micmacIGN/micmac/releases/tag/v1.2.0) vom 10.06.2026 bietet **`micmac_windows.zip`**. Das [zugehörige README](https://github.com/micmacIGN/micmac/blob/v1.2.0/README.md#windows-10) beschreibt Windows 10. Diese Angaben belegen die Bezugsquelle, noch keinen erfolgreichen Lauf auf dem Auswerterechner.

- [Windows-ZIP direkt vom Upstream](https://github.com/micmacIGN/micmac/releases/download/v1.2.0/micmac_windows.zip)
- Veröffentlichte Dateigröße: **42.521.668 Bytes**
- Veröffentlichter SHA-256: `7f2fcfb59c6dcc0b5db93fed9de01b413b279e589a7cdd423ab29af085af3c35`

Diese Werte stammen aus den offiziellen GitHub-Release-Metadaten, geprüft am 01.11.2026; das Archiv wurde hier nicht heruntergeladen oder unabhängig vermessen. Sie gelten genau für dieses Asset. Eine spätere andere Version nicht anhand dieses Hashwerts prüfen.

Der Nutzer beschafft und entpackt MicMac **separat**. SolarCheck lädt, installiert und bündelt das Paket nicht. Die bestehende [Komponentenprüfung](FREIE_ORTHOFOTO_WERKZEUGE.md) gilt weiter: CeCILL-B-Hauptprojekt, gesonderte SiftPP-/Triangle-Bedingungen. Der [vorbereitete Arbeitsablauf](MICMAC_LOKALER_RGB_THERMAL_ABLAUF.md) sieht Digeo/Ann statt des alten SiftPP-Helfers vor. Ein passender Download allein ist keine Freigabe aller Paketkomponenten.

## Schritte am Auswerterechner

1. Auf der offiziellen Release-Seite unter **Assets** `micmac_windows.zip` herunterladen. Die Quelldateiarchive „Source code“ sind kein Ersatz für das Windows-Paket. Keine Kundenbilder für diesen Schritt verwenden.
2. Optional die heruntergeladene Datei in PowerShell prüfen, mit ihrem tatsächlichen Pfad:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\DEIN-DOWNLOADORDNER\micmac_windows.zip'
   ```

   Den Wert mit dem oben veröffentlichten SHA-256 vergleichen. Bei Abweichung das Paket nicht ausführen, sondern zunächst Dateiversion und Download prüfen.
3. Das **gesamte ZIP** über „Alle extrahieren“ in einen separaten Werkzeugordner entpacken, beispielsweise `C:\Tools\MicMac`. Nicht nur `mm3d.exe` herauskopieren: Bibliotheken, Ressourcen und Hilfsprogramme brauchen die vorgesehene Verzeichnisstruktur. Je nach Archiv gibt es darunter noch einen zusätzlichen Ordner.
4. Im entpackten Ordner `bin\mm3d.exe` suchen. Der tatsächliche Pfad kann beispielsweise `C:\Tools\MicMac\micmac\bin\mm3d.exe` heißen; diesen Beispielpfad nicht ungeprüft übernehmen. Keine Bild- oder Kundenordner durchsuchen.
5. Zunächst nur den Programmstart in PowerShell testen, ohne Bilddateien oder Projektpfade:

   ```powershell
   & 'C:\TATSAECHLICHER-MICMAC-ORDNER\bin\mm3d.exe'
   ```

   Erwartet wird eine Hilfe-/Kommandoliste. Das ist nur ein Starttest, kein Photogrammetrie- oder Qualitätsnachweis. Falls eine DLL oder Laufzeit fehlt, den genauen Meldungstext festhalten; keine DLLs von fremden Downloadseiten beschaffen und keine Windows-Sicherheitsfunktion pauschal abschalten.
6. Den tatsächlichen `mm3d.exe`-Pfad und das Ergebnis des Starttests für die Fortsetzung notieren. Version ist bei Verwendung dieses unveränderten Pakets v1.2.0. Noch keine Bilder zur Prüfung hochladen.

Für diesen ersten Test ist keine dauerhafte Änderung der Windows-PATH-Variable nötig: Der vollständige Aufrufpfad genügt. Das Upstream-README nennt für spätere Aufrufe das `bin`-Verzeichnis in PATH; `binaire-aux` muss nicht zusätzlich in PATH aufgenommen werden. Kein Docker, WSL oder Betriebssystemwechsel ist Teil dieser Anleitung.

## Danach im bestehenden Entwicklungsblock VERT-01B2

Nach dem belegten Start die benötigten Standardkommandos/Helfer der konkreten Installation prüfen und den [RGB-/Thermal-Standardablauf](MICMAC_LOKALER_RGB_THERMAL_ABLAUF.md) lokal vorbereiten. Echte Bilder ausschließlich unter Nutzerkontrolle auf dem Auswerterechner verarbeiten. Anschließend vorhandene GeoTIFF-Paarregistrierung und Anlagenübersicht verwenden. Keine neue Engine, keine erneute Rohbildinventur und keine neue GUI-Zwischenentwicklung als Ersatz für diesen Rechenpfad.
