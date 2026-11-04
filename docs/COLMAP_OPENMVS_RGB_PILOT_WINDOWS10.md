# Lokaler RGB-Pilot – COLMAP 3.12.6 und OpenMVS 2.4.0

Der Nutzer hat diesen Pilot am 04.11.2026 bestätigt. Zielrechner: MEDION P17603, Windows 10, 64 GB RAM, Intel UHD 620 und NVIDIA MX250. Online später gegebenenfalls anpassen; jetzt den Offline-Weg praktisch belegen. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der neue Starter verarbeitet **alle bereits importierten RGB-JPGs eines ausdrücklich gewählten Projekts**. Er liest die vorhandene SQLite nur lesend, erstellt bytegleiche Arbeitskopien und einen neuen privaten Jobordner. Er verändert keine Originale, Projekt-/Thermaldateien oder Freigaben. Es ist ein separater Pilotstarter; das bisherige SolarCheck-Hauptfenster bekommt noch keinen neuen Menüpunkt. Bestehende Importe und Projekte weiterverwenden.

**Noch kein echter Windows-10-/RGB-/Thermal-Qualitätsnachweis.** Automatisierte Tests verwenden synthetische Dateien und simulierte Fremdprogramme; sie prüfen Dateireferenz, Prozessaufrufe, Speicherung und Abbruch. COLMAP/OpenMVS rechnen erst auf dem Rechner des Nutzers nach Klick auf „Pilot starten“. Der Pilot erzeugt zunächst nur RGB, kein Ersatz-Thermal und kein automatisch registriertes Rasterpaar.

## 1. Zwei Standardprogramme separat bereitstellen

Beide ZIPs manuell herunterladen und vollständig in getrennte Werkzeugordner entpacken, beispielsweise `E:\Tools\COLMAP-3.12.6` und `E:\Tools\OpenMVS-2.4.0`. DLLs/Plugins bei ihren Programmen lassen. Bestehendes MicMac bleibt unverändert. Der Pilot lädt/installiert keine Programme, Python-Pakete oder Treiber.

- **[COLMAP 3.12.6 Windows CUDA ZIP](https://github.com/colmap/colmap/releases/download/3.12.6/colmap-x64-windows-cuda.zip)**. Dieses Release verwendet CUDA 12.6.2 und ist der ältere GPU-Prüfkandidat für Pascal. COLMAP 4.2.1 mit CUDA 13.2 nicht als MX250-GPU-Version verwenden. Im Pilot die tatsächliche **`bin\colmap.exe`** auswählen, keine BAT-Datei.
- **[OpenMVS 2.4.0 Windows x64 ZIP](https://github.com/cdcseacave/openMVS/releases/download/v2.4.0/OpenMVS_Windows_x64.zip)**. Für diesen Pilot das normale CPU-ZIP verwenden. Später den Ordner auswählen, in dem `InterfaceCOLMAP.exe`, `DensifyPointCloud.exe`, `ReconstructMesh.exe`, `RefineMesh.exe` und `TextureMesh.exe` liegen; ein gemeinsamer `bin`-Unterordner wird ebenfalls gefunden.

Für den Pilot kein zusätzliches CUDA-Toolkit installieren; zunächst das vollständige COLMAP-Archiv verwenden. Die MX250-Version und der installierte Treiber sind hier noch nicht durch einen echten Programmstart geprüft. Der Starter prüft zunächst die Werkzeugversionen. Falls der GPU-Weg nicht startet, bleibt **[COLMAP 3.12.6 NoCUDA](https://github.com/colmap/colmap/releases/download/3.12.6/colmap-x64-windows-nocuda.zip)** mit deaktiviertem NVIDIA-Häkchen eine Alternative. Kein automatischer Treiberwechsel und kein Windows-11-Wechsel.

## 2. Pilot-Quellcode entpacken und starten

Den [festgelegten Pilot-Quellcode als ZIP herunterladen](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/archive/4111aed3e09e238e69f9d81c7433c65a59cd451b.zip) und in einen neuen Programmordner auf F: entpacken. Code-Stand `4111aed3e09e238e69f9d81c7433c65a59cd451b`; die heruntergeladene Quellen-ZIP wurde hier geöffnet und Starter sowie beide Fachmodule byteweise gegen den Commit geprüft. Keine Fremdprogramm-Binaries wurden dafür heruntergeladen oder ausgeführt. Alten Programmordner, vorhandene Python-Umgebung und Datenbank behalten. Die Quellcode-ZIP enthält keine Fremdprogramm-Binaries oder Kundenbilder.

1. Das normale SolarCheck-Fenster schließen, damit während des Piloten keine Importe geändert werden.
2. Im **neu entpackten Ordner mit `src` und `scripts`** PowerShell öffnen.
3. Mit dem vorhandenen Python starten:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' '.\scripts\MCM_SolarCheck_RGB_PILOT.py'
```

Dieser Befehl startet den neuen Pilotdialog. Er verwendet Quellcode aus der neuen ZIP und Pakete aus der bestehenden Python-Umgebung; keine Installation/Migration. Der bisherige Schritt-115-Starter öffnet weiterhin seinen alten festgelegten Programmstand und ist nicht der Einstieg für diesen Pilot.

## 3. Vorhandenes Projekt ausdrücklich auswählen

Im Pilotdialog nacheinander wählen:

1. **Vorhandene Projektdatei:** dieselbe SolarCheck-SQLite mit dem bereits importierten Dachprojekt. Es wird keine neue leere DB angelegt. Nach der Dateiwahl das richtige Projekt aus der Liste wählen; es wird nicht automatisch das erste Projekt gestartet.
2. **COLMAP:** die `colmap.exe` der entpackten Version 3.12.6.
3. **OpenMVS:** den Programmordner der entpackten Version 2.4.0.
4. **Privater Ausgabeordner:** vorhandenen separaten Ordner, beispielsweise `F:\Auswertung-Pilot`. Er muss außerhalb von Originalbildordnern und Git liegen. Ergebnisse nicht in den Programmquellcode oder einen Cloud-Synchronisationsordner legen.
5. **Ziel-CRS:** zunächst leer lassen; aus den echten gespeicherten Kamerapositionen wird eine passende eindeutige WGS84-UTM-Zone bestimmt. Bei uneindeutiger Zone ein tatsächlich passendes metrisches Zielsystem angeben, kein geratenes EPSG. Originalhöhen werden erhalten; ihr Höhenbezug ist nicht unabhängig geprüft.
6. Für den ersten GPU-Versuch das NVIDIA-Häkchen gesetzt lassen. Es betrifft COLMAP-Merkmale/Bildabgleich; OpenMVS wird in diesem Pilot auf CPU betrieben.

Für den ersten Vergleich ein kleines, zusammenhängendes, bereits importiertes Dachprojekt wählen. Keine neue ZIP-/EXIF-Inventur oder erneuter Import nötig. Auf **„Pilot starten“** klicken. Jetzt beginnt das Lesen/Kopieren der Original-JPGs. Importierte Kamerapositionen mit Länge/Breite/absoluter Höhe sind erforderlich; fehlende Werte werden nicht erfunden. Keine externe RGB-Kalibrierungsdatei oder RTK-Fix als allgemeine Startvoraussetzung.

## 4. Ablauf und gespeichertes Ergebnis

Der Dialog zeigt konkrete Stufennamen. Hauptschritte:

- COLMAP: Merkmale → Bildabgleich → Kameralösung → Vollständigkeitsprüfung → Positionsabgleich → Entzerrung.
- OpenMVS: COLMAP-Import → dichte Rekonstruktion → Oberfläche → Verfeinerung → Textur → Orthobild. Vorhandene Standardprogramme übernehmen diese Arbeit, keine neue eigene Engine.
- Rasterio/GDAL übernimmt das bereits gerenderte RGBA-PNG mit belegtem Rastertransform in **`rgb_ortho.tif`**. Keine neue Pixelorthorektifizierung oder erfundene Georeferenz.

Es wird nicht stillschweigend das größte Teilmodell gewählt: Wenn COLMAP mehrere getrennte Modelle oder nicht alle RGB-Aufnahmen ausrichtet, stoppt der Pilot vor der dichten Rekonstruktion. Eine einzige vollständige Kameralösung ist eine technische Mindestprüfung, keine Garantie richtiger Dachgeometrie.

Im neuen `rgb-pilot-…`-Job bleiben erhalten:

- **`rgb_ortho.tif`:** fertiges RGB-GeoTIFF, ausdrücklich ungeprüfte Darstellung. Mit IrfanView am lokalen Rechner öffnen; später vorhandenen GeoTIFF-Import verwenden.
- **`laufzeiten.json`:** Status, Bildanzahl, gesamte Laufzeit und Laufzeit pro Stufe; ohne Bildnamen, Quellpfade, Kamerakoordinaten oder rohe Prozessausgaben. Auch ein fehlgeschlagener Job bekommt diese Zusammenfassung.
- **`job.json`, `input-map.json`, `references.txt`, `alignment.txt`:** private lokale Herkunft/Koordinaten/Dateizuordnung; nicht nach GitHub/CI/Chat hochladen.
- **`step-….log` und weitere Werkzeugdateien:** private Rohprotokolle, Kameralösungen, Arbeitsbilder und Zwischenmodelle bleiben lokal. Nicht pauschal übertragen.

**„Ausgabeordner öffnen“** öffnet nach Erfolg den gespeicherten Job. Die alte MicMac-Paaranzeige im Hauptprogramm wird nicht automatisch ersetzt; das neue Pilot-TIFF direkt aus diesem Jobordner ansehen. Nach Schließen des Dialogs bleiben TIFF, Metadaten und Laufzeiten erhalten; für die Sichtprüfung nicht erneut rechnen. Der Pilot verändert die vorhandene Projektregistrierung nicht. Ein RGB-/Thermal-Paar wird erst nach erfolgreichem Thermal-Nachweis über den vorhandenen atomaren Paarimport übernommen.

**Abbrechen/Schließen während eines Laufs:** der eigene externe Prozessbaum wird beendet, der Dialog wartet auf die Beendigung. Keine Ergebnisübernahme oder Projektfreigabe; private Zwischenstände bleiben erhalten. Bei Fehlern nennt der Dialog nur die Stufe und relative Protokolldatei. Originale und Datenbank bleiben unverändert. Ein erneuter Start erzeugt einen frischen Job; kein automatisches Resume oder Überschreiben früherer Ergebnisse.

## 5. Lokale Abnahme vor weiterer Integration

Am neuen RGB-Ergebnis bei nativer Auflösung prüfen: vollständige Dach-/PV-Flächen, zusammenhängende gerade Modulränder, keine versetzten Fragmente/Doppelkonturen, sichtbare Datenlücken und plausibel belegte Lage. Anschließend mit dem unabhängig erzeugten WebODM-RGB vergleichen. Laufzeiten nur mit Bildanzahl, Recheneinstellungen und tatsächlichem Ergebnis vergleichen; keine Geschwindigkeit aus der NVIDIA-Karte allein ableiten.

Für eine erste Rückmeldung reichen Erfolg/Fehlerstufe und die nichtgeografische `laufzeiten.json`. Keine Original-JPGs, komplette Jobordner, produktive DB oder GPS-Dateien übertragen. Thermaldaten nicht als RGB oder ungeprüftes RGB nicht als Thermal registrieren. Keine Fach-/Temperatur-/Vermessungsfreigabe aus einem gültigen GeoTIFF-Header.

## Technischer Vertrag und spätere Online-Anpassung

`services/colmap_openmvs_pilot.py` hat keine Tk-/Qt-Abhängigkeit. `run_rgb_pilot(frames, config, …)` bekommt explizite Eingaben, Werkzeug-/Arbeitsverzeichnisse, Fortschritts-/Abbruchfunktionen und eine optionale Eingabesignaturprüfung. `read_rgb_project` ist ein getrennter SQLite-read-only-Adapter. Eine spätere Online-Worker-Anbindung kann autorisierte lokale Jobdateien und Ressourcen über dieselbe Schnittstelle liefern; derzeit keine Upload-/Cloud-Verarbeitung, Queue oder neue Online-API implementiert.

Georeferenz: tatsächliche WGS84-Kamerapositionen via installiertem PROJ offline in ein passendes metrisches Zielsystem, gemessene Positionen um einen gespeicherten lokalen Ursprung verschoben. COLMAP `model_aligner` passt ein globales Ähnlichkeitsmodell an diese Referenzen an. RANSAC-Entfernung 3 m ist ein ausdrücklich gespeicherter Ablehnungsparameter, **kein** behaupteter RTK-Fehler oder erfundenes GNSS-Gewicht. Keine Reparatur falscher lokaler Kamerageometrie durch einen CRS-Aufkleber. Große globale UTM-Koordinaten werden nicht in Float-Meshes weitergereicht.

Der Formatadapter `openmvs_orthomap.py` liest die tatsächlichen PLY-Vertices des zuletzt projizierten Meshes. OpenMVS-v2.4 definiert seine Bildgröße über die Float32-AABB mit 1,01-Rand, die maximal angeforderte Achse und den Mittelpunkt bei `(width−1)/2,(height−1)/2`. Die Kamera blickt entlang −Z, rechts ist +X, Bild-unten ist −Y. Daraus werden **nur Rastermetadaten** mit korrekter Pixelmitte→GDAL-Pixelecke gewonnen. PNG-Maße müssen genau passen; Alpha und gültige schwarze Pixel bleiben erhalten. Die gerundete TXT-Center-Datei allein wird nicht als Georeferenz verwendet. Kein Raytracing, Sampling, SfM, BA oder Meshrenderer in SolarCheck.

OpenMVS-Working-Archive werden nach dem COLMAP-Import ausdrücklich als Typ 2 gespeichert, damit die Oberfläche für die nächste Stufe erhalten bleibt. Koordinatennormalisierung wird ausgeschaltet. Texturierung erfolgt vor der Orthobild-Anforderung: Der v2.4-Quellzweig für eine direkte Orthomap-Anforderung auf untexturiertem Mesh kann die Texturierung überspringen. Der zweite Standardaufruf arbeitet deshalb auf dem tatsächlich texturierten Mesh; er kann je nach Binärstand erneut texturieren. Beide Laufzeiten werden sichtbar erfasst. Keine OpenMVS-Änderung/Fork oder neue Engine.

Parameter des ersten Piloten: COLMAP-SIFT maximal 2400 Pixel für Merkmalsextraktion, originale bytegleiche Arbeitskopien/Entzerrung; OpenMVS-Dichte/Verfeinerung Auflösungsstufe 1; Orthomap maximal 8192 Pixel; bis zu acht vorhandene CPU-Threads. Das sind Testeinstellungen, keine zugesicherte GSD/Genauigkeit. Quelle, Inputsignatur, lokaler Ursprung, tatsächlicher Rastertransform und Einstellungen bleiben im privaten Job gespeichert.

Primärquellen: [COLMAP 3.12.6 CLI](https://github.com/colmap/colmap/blob/3.12.6/doc/cli.rst), [Positionsabgleich](https://github.com/colmap/colmap/blob/3.12.6/src/colmap/exe/model.cc), [OpenMVS TextureMesh](https://github.com/cdcseacave/openMVS/blob/v2.4.0/apps/TextureMesh/TextureMesh.cpp), [Orthoprojektion/Float-Mesh](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/MVS/Mesh.cpp), [Kamera-/Pixelkonvention](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/MVS/Camera.h), [AABB](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/Common/AABB.inl), [Kamerabasis](https://github.com/cdcseacave/openMVS/blob/v2.4.0/libs/Common/Rotation.inl).

Release-SHA256 aus den offiziellen Release-Metadaten, keine hier ausgeführte Binärprüfung:

| ZIP | SHA256 |
| --- | --- |
| COLMAP 3.12.6 Windows CUDA | `bf9e01ba942df89d3dc561626e5a89300b0b09371afcdc33e17a60e9511cf081` |
| COLMAP 3.12.6 Windows NoCUDA | `7f79a1bfcaff25abdb1b264fe14328b6a573420a8efda2cc9ed7e97c867ec770` |
| OpenMVS 2.4.0 Windows x64 CPU | `0c31660c15c9ebc4c106873cf67564d9570d404aef7a6403451da1b6178b2167` |
