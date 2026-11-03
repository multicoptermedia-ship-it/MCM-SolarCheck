# Erster lokaler MicMac-Lauf und Vergleich mit der RGB-Referenz

Stand 03.11.2026 · VERT-01B2 ist technisch angebunden. **Echter RGB-Lauf auf Windows 10 erfolgt, visuelle Qualität FAIL; Thermal blockiert.** Ein vollständiges brauchbares Rasterpaar und Fachabnahme fehlen. Automatisierte Rekonstruktionstests nutzen synthetische Bilder/Fake-MicMac; die nachfolgenden realen Sichtbefunde sind davon getrennt.

**Nutzerstand 03.11.2026 / RGB-QUAL-01 FAIL:** Das benannte MicMac-RGB-GeoTIFF wurde auf ausdrücklichen Nutzerwunsch jetzt tatsächlich visuell geprüft. Technischer RGB-Abschluss ist bestätigt, Bildqualität jedoch unbrauchbar für PV-Modulprüfung. Thermal bleibt nach zwei MST-Abbrüchen blockiert; 26 RGB/26 Thermal/25 Paare, alle Thermalaufnahmen importiert. Kein vollständiges Paar registriert und keine Freigabe.

## Aktueller Schritt: letzte Höhe mit globaler Maske schummern

**Dateinamenfrage abgeschlossen:** Z_Num8_DeZoom2_STD-MALT.tif wurde zweimal genannt, AutoMask_STD-MALT_Num_7.tif und MasqPC_STD-MALT_Num8_000026.tif liegen laut Nutzer vor. Die MasqPC ist bildbezogen (Aufnahme26), nicht die globale Geländemaske. AutoMask7 ist der Standardkandidat: Malt nutzt die letzte Quantisierungsmaske auch nach der nachfolgenden Dequantisierung. Lokale räumliche Übereinstimmung trotzdem vor GrShade prüfen. Keine weiteren Ort-Dateien/Dateinamen oder Roh-XMLs anfordern.

1. Im Explorer **denselben** privaten Laufordner `rgb\MEC-Malt` öffnen.
2. In die Explorer-Adresszeile `powershell` tippen und Enter drücken. Die Konsole muss in diesem MEC-Malt-Ordner starten.
3. Den folgenden Block vollständig einfügen. Benötigt vorhandenes Python auf F: mit dem bereits verwendeten Rasterio; keine Installation. Die vorhandenen XMLs `Z_Num7_DeZoom2_STD-MALT.xml` und `Z_Num8_DeZoom2_STD-MALT.xml` bleiben lokal.

Der Block prüft die Rasterlage/-größe aus den beiden XMLs sowie die tatsächlichen TIFF-Größen/Bandzahlen. Höhen-/Pixelauflösung bestimmen den Darstellungsfaktor FZ; kein erfundener Maßstab. Diese Gleichheitsprüfung bestätigt weder GNSS-Genauigkeit noch Kamerageometrie. Bei Fehlern wird GrShade nicht gestartet. Bei passenden Eingaben erzeugt nur MicMac GrShade eine neue, eindeutig benannte 8-Bit-Schummerung und ein lokales Protokoll; alle bisherigen Ergebnisse bleiben bestehen. Keine Original-JPGs/SQLite werden gelesen, keine Photogrammetrie berechnet und nichts hochgeladen.

### PowerShell-Block

```powershell
@'
import sys, math, warnings, xml.etree.ElementTree as E
from pathlib import Path
import rasterio
warnings.filterwarnings('ignore', category=rasterio.errors.NotGeoreferencedWarning)
z = Path('Z_Num8_DeZoom2_STD-MALT.tif')
m = Path('AutoMask_STD-MALT_Num_7.tif')
try:
    a = E.parse('Z_Num7_DeZoom2_STD-MALT.xml').getroot()
    b = E.parse('Z_Num8_DeZoom2_STD-MALT.xml').getroot()
    for tag in ('NombrePixels', 'OriginePlani', 'ResolutionPlani'):
        ga = tuple(float(v) for v in a.findtext(tag).split())
        gb = tuple(float(v) for v in b.findtext(tag).split())
        if ga != gb or not all(math.isfinite(v) for v in ga + gb):
            raise ValueError()
    dx, dy = (float(v) for v in b.findtext('ResolutionPlani').split())
    dz = float(b.findtext('ResolutionAlti'))
    if dx == 0 or abs(dx) != abs(dy) or not math.isfinite(dz) or dz == 0:
        raise ValueError()
    fz = dz / abs(dx)
    if not math.isfinite(fz):
        raise ValueError()
    size = tuple(int(v) for v in b.findtext('NombrePixels').split())
    with rasterio.open(z) as h, rasterio.open(m) as mask:
        if h.count != 1 or mask.count != 1 or (h.width, h.height) != size or (mask.width, mask.height) != size:
            raise ValueError()
except Exception:
    print('Raster-/Maskenpruefung fehlgeschlagen; nichts gestartet.')
    sys.exit(1)
import subprocess, uuid
out = Path('MCM_RGB_Hoehenpruefung_' + uuid.uuid4().hex + '.tif')
log = out.with_suffix('.log')
try:
    with log.open('xb') as protokoll:
        result = subprocess.run(
            [r'E:\Tools\MicMac\bin\mm3d.exe', 'GrShade', str(z),
             'Mask=' + str(m), 'Out=' + str(out), 'FZ=' + str(fz), 'Visu=0'],
            stdout=protokoll, stderr=subprocess.STDOUT, timeout=600)
except (OSError, subprocess.TimeoutExpired):
    print('GrShade nicht beendet; nur das neue lokale Protokoll pruefen.')
    sys.exit(1)
if result.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
    print('GrShade fehlgeschlagen; nur das neue lokale Protokoll pruefen.')
    sys.exit(1)
print('Erstellt: ' + out.name)
'@ | & "F:\MCM-SolarCheck\.venv\Scripts\python.exe" -
```

Nur nach **„Erstellt: …“** die neue Datei `MCM_RGB_Hoehenpruefung_….tif` in vorhandenem **IrfanView** öffnen. Zusätzlich `AutoMask_STD-MALT_Num_7.tif` ansehen. Für die Rückmeldung eine gezielte PNG/JPG-Ansicht von Schummerung und Maske ohne Koordinaten genügt; kein ursprüngliches Höhenmodell/Geo-XML/Protokoll hochladen. Bei einer festen Fehlermeldung nur diese kurze Meldung nennen, keinen neuen Foto-/Orthofotolauf starten. Das neue Protokoll bleibt lokal.

Auf abrupte Plateaus, Sprünge oder streifenweise gegeneinander versetzte Flächen **innerhalb gültiger Maskenbereiche** achten; Maskenränder/ungültiges Gelände nicht als reale Dachform auslegen. Eine auffällige Schummerung trennt fehlerhafte Oberfläche und falsche Kameraorientierung noch nicht allein. Schattenbild und Metadatenskalierung sind kein unabhängiger Höhen-/Vermessungsnachweis. RGB bleibt FAIL, Thermal blockiert.

**Öffentliche Quellen v1.2.0:** [bildbezogene MasqPC-Namen](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/MICMAC/PartiesCachees.cpp#L315), [globale AutoMask/Metadatenreferenz](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/MM-Malt.xml#L85), [abschließende Dequantisierung](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/MM-Malt.xml#L821), [FileOriMnt-Auflösungen](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_GEN/ParamChantierPhotogram.xml#L443), [GrShade-Optionen](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_image/CPP_GrShade.cpp#L97) und [FZ-Anwendung](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_image/CPP_GrShade.cpp#L224). Keine ungeprüften Optionen wie DeZoom ergänzen. Kopierblock mit 13 synthetischen Proben einschließlich Fake-Prozess getestet; **echter GrShade-/Windows-Lauf steht noch aus**. Source-Anbindung, Starter und installierte App unverändert.

## Abgeschlossene Sichtprüfung: fünf Einzelorthos vor Tawny

Der folgende Befund bleibt gültig; die anschließende Dateinamenfrage ist inzwischen beantwortet und wird durch den obigen konkreten GrShade-Schritt ersetzt.

**Sichtprüfung erfolgt, keine weiteren Beispiele/Screenshots anfordern:** Auf ausdrücklichen Nutzerwunsch nur die fünf neuen Drive-Dateien Ort_000009.tif und Ort_000014.tif bis Ort_000017.tif gelesen. Jeweils einzeln eine Gesamtansicht und zusätzlich drei native 1200×800-Ausschnitte aus 09/14/17 geprüft. Ort_000021.tif wurde weiterhin nicht gelesen; die neuen fünf Dateien genügen zum Nachweis der zuvor beschriebenen Einzelortho-Fehler. Keine Originalbilder/anderen Kundendaten oder Referenzraster abgerufen.

Alle fünf zeigen abgesetzte Dach-/PV-Stücke und harte interne Übergänge. In nativen Ausschnitten sind Zell-/Modulränder geknickt, verschoben und unterbrochen; es geht nicht nur um schwarze Außenränder oder unterschiedliche Bildabdeckung. Befund unabhängig vom Nutzerbetrachter und Mehrlayerdarstellung bestätigt. Nutzer korrigiert Viewerangabe: **IrfanView zum Ansehen**, WebODM separat zur Erzeugung seiner externen Referenz. Keine WebODM-Anbindung daraus ableiten.

**Eingrenzung:** Mindestens ein Fehler liegt bereits in Malt-Einzelorthos, vor Tawny und finalem GeoTIFF-Export. Ein reiner Naht-/EPSG-/Exportfix reicht nicht. Höhenmodell, Kameraorientierung/Selbstkalibrierung und Einzelbild-Projektion sind noch nicht getrennt. Wiederkehrende Brüche machen die gemeinsame Oberfläche zu einem Prüfkandidaten, nicht zur bewiesenen alleinigen Ursache. Keine neuen SfM-/Stitching-/3D-Algorithmen programmieren und nicht blind Modell/Schwellen ändern.

Alle fünf sind uint8-RGB-Arbeits-TIFFs ohne eingebettetes CRS/NoData/Alpha (all_valid). Separate Worldfiles/Geometrie-/Gültigkeitsmasken liegen hier nicht vor. Das beweist keine fehlende lokale Georeferenz oder ungültige Maskenerzeugung; keine absoluten Weltkoordinaten/Flächenfehler aus Einzel-TIFFs behaupten. Vorschauen/Originale bleiben außerhalb Git/CI.

### Genau nächster Schritt: vorhandenes Höhenmodell mit passender Maske

Im selben privaten Laufordner `rgb\MEC-Malt` **nur die Dateinamen** der letzten Stufe `Z_Num…DeZoom2…tif` und der vorhandenen `Masq…`/`AutoMask…` zurückmelden. Keine Pfade, Originale, neuen Ort-Dateien oder georeferenzierten XML-Inhalte hochladen. Die tatsächlich passende Maske anhand gleicher Stufe/Auflösung bzw. referenzierender MicMac-Metadaten bestimmen; bei Unklarheit nicht irgendeine Maske zuweisen. Damit lässt sich der konkrete Standardbefehl ohne geratenen Dateinamen vorbereiten.

Danach MicMacs vorhandenes **GrShade** für eine qualitative Schummerung des bereits berechneten Höhenmodells mit Maskenberücksichtigung und eindeutiger **neuer** Ausgabedatei verwenden; Originale nicht überschreiben, keine Photogrammetrie neu rechnen. Ausgabe mit vorhandenem IrfanView ansehen; vorerst keine zusätzliche Software/Installer oder neue Diagnosearchitektur.

[Geprüfter öffentlicher Quelltext v1.2.0 CPP_GrShade.cpp](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_image/CPP_GrShade.cpp#L97): Out/Mask/Visu unterstützt, Ausgabe uint8, **kein DeZoom-Parameter**. Keine unbewiesenen Optionen in Kopierbefehle aufnehmen. Noch kein GrShade-Lauf mit Nutzerdaten/Windows-Abnahme erfolgt. Schummerung zeigt berechnete Werte, bestätigt weder echte Höhen noch Ursache; ungültige/maskierte Bereiche und Maskenrand-Artefakte berücksichtigen. Stereo-/Kamerakontrolle bleibt bei auffälliger Oberfläche weiterhin nötig. Thermal-Rigweg zurückgestellt, keine Temperatur-/Fachfreigabe.

## Historischer Transferblocker: Ort_000021.tif

Die frühere Sichtprüfungsanfrage ist durch die fünf neuen Beispiele erfüllt; folgenden Abschnitt als Historie erhalten, nicht erneut Ort_000021/Screenshots anfordern.

Nutzer hat die Einzelbilder angesehen und beschreibt frei verteilte, teils von der zusammenhängenden Fläche abgesetzte Bildstücke. Dazu wurde **Ort_000021.tif** ausdrücklich zur Kontrolle hochgeladen. Obwohl die Nachricht Screenshot sagt, liegt eine TIFF-Datei vor. Der direkte Dateitransfer ist wegen über 32 MiB blockiert. Gezielte Suche im bekannten öffentlichen Drive-Ordner fand diese Datei auch unter Variante Ort_000021.JPG.tif nicht. Daher **noch keine unabhängige Sichtprüfung dieses Einzelorthos**. Nicht so darstellen, als sei der Anhang bereits gesehen worden; die frühere Sichtprüfung des RGB-Gesamtbilds bleibt getrennt belegt.

Als nächstes ein **PNG-/JPG-Screenshot, der nur Ort_000021.tif zeigt**, ohne zusätzliche Rasterlayer oder Koordinatenanzeigen. Das grenzt echte Fragmente innerhalb einer Datei von einer gemeinsamen Anzeige mehrerer gegeneinander versetzter Raster ab. Es geht nur um die bereits ausdrücklich zur Prüfung bereitgestellte Datei, keine pauschale Freigabe weiterer Bildbestände. Kein neuer MicMac-Lauf/Installationsschritt und kein Originalserien-/Protokollupload.

Wenn die Brüche in diesem isolierten Einzelortho sichtbar sind, liegt mindestens ein Fehler schon vor dem Tawny-Mosaik. Das trennt noch nicht Kameraorientierung/Selbstkalibrierung von dichten Oberflächen-/Orthorektifizierungsfehlern. Aus schwarzem Außenrand, fehlendem Sichtbereich oder großen GPS-Anpassungsresiduen ohne RTK keine vorschnelle Ursache ableiten. RGB bleibt FAIL, Thermal blockiert.

## Bereits angefragter Einzelortho-Schritt vor Tawny

Die Nutzerrückmeldung liegt nun vor (oben); Dateien nicht erneut pauschal ansehen lassen. Für die gezielte noch offene Sichtprüfung nur das genannte Einzelortho isoliert darstellen.

**Zahlen vollständig – nicht erneut anfordern:** MoyenneDistPlani 8.69203144801449668 m, MoyenneDistAlti 1.08247549537456567 m; mittlerer 3D-Abstand 8.788591 m, Maximum 20.126524 m. Ohne RTK-Fix, echte GNSS-Genauigkeit unbekannt. Horizontaler Anteil dominiert, Höhe erklärt die großen seitlichen Versätze nicht allein. Keine RMS-/Vermessungsgenauigkeit aus diesen Anpassungsresiduen machen; Kamera-/GPS-Ursache noch offen. Die Mittelwerte lassen sich nicht durch einfachen Pythagoras ineinander umrechnen.

Im **gleichen bestehenden MicMac-Laufordner** den Unterordner `rgb\Ortho-MEC-Malt` öffnen und zwei vorhandene RGB-TIFFs mit Namen beginnend mit **`Ort_`** lokal ansehen. Diese Einzelorthos wurden von Malt erzeugt, bevor Tawny das Gesamtmosaik zusammengesetzt hat. Kein neues Programm/keine Berechnung dafür starten. Falls die Dateien fehlen oder der vorhandene Betrachter sie nicht öffnet, genau das als Text zurückmelden; keine neue Lauf-/Installationsschleife beginnen.

Beurteilen, ob **innerhalb einer zusammenhängenden Modulfläche eines Einzelorthos** bereits Modul-/Zellraster zerrissen, verzogen oder gegeneinander versetzt sind. Unterschiedliche äußere Bildabdeckung und schwarze Außenränder sind allein kein Fehler. Nur den Eindruck als Text zurückmelden; Dateien, Koordinaten und Screenshots bleiben lokal.

- Fehler bereits im Einzelortho: mindestens eine Ursache liegt vor Tawny, bei Orientierung/Oberfläche/Einzelbild-Orthorektifizierung; alleinige Änderung der Mosaiknaht kann das nicht beheben.
- Einzelorthos für sich plausibel: anschließend deren tatsächliche gemeinsame Lage/Überlappung prüfen. Dies beweist **keinen Tawny-Fehler**, denn falsche Kameraposen können intern glatte, aber gegeneinander versetzte Einzelbilder liefern.

**180°-Vermutung gezielt eingeordnet:** Im öffentlichen MicMac-v1.2.0-Standardpfad berücksichtigt Digeo lokale Merkmalswinkel und normiert den Deskriptor darauf. [cImDigeo.cpp orientateAndDescribe](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_image/Digeo/cImDigeo.cpp#L838), [cImInMem.cpp Winkelbestimmung](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_image/Digeo/cImInMem.cpp#L592), [Orientierungsnormalisierung im Deskriptor](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_image/Digeo/cImInMem.cpp#L773). Ein alternativer Compile-Zweig DIGEO_NO_ANGLE existiert; Version/Build des Nutzerprogramms nicht unabhängig bestimmt. Daher weder fehlende Drehungsunterstützung noch konkrete Binärkonfiguration als bewiesen darstellen. Kein blindes Drehen der JPGs/Matcherwechsel.

**Vorhandene Standardprodukte belegt:** [MM-Malt.xml lädt OrthoFinal](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/MM-Malt.xml#L61), [MM-Malt-OrthoFinal.xml MakeOrthoParImage/Ort_-Präfix](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/MM-Malt-OrthoFinal.xml#L15). Noch keine Ursache behoben, kein neues Orthofoto erzeugt. RGB bleibt FAIL, Thermal blockiert; mangelhafte RGB-Geometrie nicht auf Thermal übertragen.

## Abgeschlossene Komponentenprüfung: Lage-/Höhenanteile

Die beiden Werte wurden inzwischen vollständig vom Nutzer zurückgemeldet (siehe oben). Folgende frühere Anleitung als Historie erhalten, nicht erneut ausführen lassen.

**Kennzahlenprüfung bereits ausgeführt – keinen erneuten Download/Prüflauf anfordern.** Nutzer meldet unter Windows: 26 RGB-Arbeitskopien, je 26 Rel/Ground, keine fehlenden/fremden Orientierungsdateien; 41 Tapas-Iterationen, letzte mit 26 Bildern, AverageResidual 1.207238. GPS-Abgleich 26 Zentren, MoyenneDist 8.788591 m, größte Dist 20.126524 m. Das bestätigt die lokale Lesefunktion des Helfers, keine richtige Bildgeometrie. WorstRes fehlt in der übermittelten Ausgabe; keinen Wert ergänzen.

MicMac verwendet hier GPS erst nach Tapas zur globalen Ähnlichkeitstransformation mit CenterBascule. Diese Stufe verschiebt/dreht/skaliert das gesamte Netz, korrigiert keine einzelnen Fehlzuordnungen durch lokale Bundle Adjustment. Der arithmetische mittlere 3D-Abstand beträgt rund 8,79 m, nicht RMS; Maximum rund 20,13 m. Ohne bekannte GNSS-Genauigkeit und Komponenten ist die Ursache noch offen. 180°-Flugwende bleibt Hypothese. Eine andere globale Referenz allein erklärt nicht automatisch die Restabweichungen nach Anpassung. RGB-FAIL bleibt, auch bei kleinen Bildresiduen.

Im **selben** privaten Laufordner die vorhandene Datei `rgb\Ori-Ground\Result-Center-Bascule.xml` im Texteditor öffnen. Nur die Zahlen zwischen folgenden Tags nachsehen und zurückgeben:

- `MoyenneDistPlani`: mittlerer horizontaler Abstand in Metern.
- `MoyenneDistAlti`: mittlerer absoluter Höhenabstand in Metern.

Die Datei enthält zusätzlich private Koordinaten/Transformationen; ausschließlich die zwei Zahlen mitteilen. Datei nicht bearbeiten, nicht vollständig hochladen. Kein weiterer MicMac-Lauf und keine neue Installation. Nutzer bestätigt Flug ohne RTK-Fix. Die tatsächliche GNSS-Genauigkeit ist unbekannt; keine zentimetergenaue Referenz oder beliebige GPS-Gewichte daraus ableiten. Die gemeldeten Anpassungsresiduen allein beweisen keinen SfM-Fehler. Sichtbarer RGB-FAIL bleibt bestehen.

**Quellbelege v1.2.0:** [Apero-Center-Bascule.xml fixierte Kamera-/Poseparameter](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/Apero-Center-Bascule.xml#L89), [Basculement.cpp Kennzahlenbildung](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/Apero/Basculement.cpp#L953). Hoher Lage- oder Höhenanteil grenzt den nächsten Prüfschritt ein, authentifiziert weder die GPS-Werte noch die Rekonstruktion. Keine automatische Entscheidung für feste Kameraparameter, GPS-Gewichte, Campari-BA oder neuen Malt-Lauf. Danach vorhandene Orientierung/Oberfläche anhand dieser Evidenz gezielt beurteilen.

## Abgeschlossene Kennzahlenprüfung: vorhandene Kamera-Prüfergebnisse

Die folgende Anleitung bleibt zur Wiederverwendung dokumentiert; die aktuelle Nutzerprobe ist abgeschlossen und die Zahlen stehen oben.

Die [einzelne Python-Datei](../scripts/MCM_SolarCheck_MicMac_RGB_Pruefung.py) separat in Downloads speichern. SolarCheck-Programm/ZIP/Starter bleiben unverändert. Mit vorhandenem Python starten:

```powershell
& "F:\MCM-SolarCheck\.venv\Scripts\python.exe" "$env:USERPROFILE\Downloads\MCM_SolarCheck_MicMac_RGB_Pruefung.py"
```

Im Dateidialog das **ursprüngliche** `rgb_ortho.tif` im privaten MicMac-Laufordner unter `F:\Auswertung1` wählen. Eine Downloads-/Drive-Kopie hat die benötigten Nachbarordner nicht. Falls der Dateidialog nicht verfügbar ist, den vollständigen lokalen TIFF-Pfad als zusätzliches Argument angeben. Abbruch ändert nichts.

Keine Bildpixel oder einzelnen Pose-/Kalibrierungsdateien werden gelesen. Das Skript zählt nummerierte Arbeitskopien/zugehörige Orientierungsdateien und liest nur zwei vorhandene Prüf-XMLs. Nur die bereinigte Konsolenausgabe zurückgeben; Rohdateien/Koordinaten bleiben lokal. Nichts wird gespeichert, installiert, hochgeladen, rekonstruiert oder registriert.

- `Rel`/`Ground`: Orientierungsdateien, fehlende und ohne passende RGB-Arbeitskopie; gleiche Anzahl darf falschen Kamerasatz nicht verdecken.
- `Tapas`: letzte vorhandene Iteration, dortige Bildanzahl, `AverageResidual` und gegebenenfalls `WorstRes`. Originalfeldnamen statt erfundener Qualitätsgrenzen. Fehlende/unlesbare/unbekannte XMLs oder ungültige Zahlen werden ausdrücklich markiert.
- `GPS_Abgleich`: Anzahl gespeicherter Kamerazentrumsresiduen, `MoyenneDist`, größte `Dist`; bei metrischen Projektpositionen metrische Anpassungsabweichungen, kein unabhängiger Genauigkeitsnachweis.

Dies grenzt die nächste Prüfung ein, ist **keine automatische Diagnose oder Freigabe**. Kleine Residuen können auch bei falschen Zuordnungen in gleichförmigen Modulrastern auftreten; RGB-FAIL bleibt bestehen. Danach vorhandene Malt-Oberfläche gezielt prüfen; keine blinden Parameterwechsel/Neuberechnung.

**Öffentliche MicMac-v1.2.0-Quellen:** [Apero-Glob-New.xml ExportResiduXml](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/Apero-Glob-New.xml#L1153), [ParamApero.xml Kennzahlenschema](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_GEN/ParamApero.xml#L1811), [Apero-Center-Bascule.xml NameExport](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_MicMac/Apero-Center-Bascule.xml#L84), [ParamChantierPhotogram.xml Ergebnis](https://github.com/micmacIGN/micmac/blob/v1.2.0/include/XML_GEN/ParamChantierPhotogram.xml#L2041). Installierte Windows-Version nicht bestimmt; Abweichungen nicht als Erfolg übergehen. Zwölf synthetische Tests lokal grün; echte Windows-10-Ausgabe offen.

## Aktueller Einstieg 03.11.2026: RGB-Geometrie prüfen, kein neuer Gesamtlauf

**Sichtprüfung abgeschlossen – nicht erneut dieselbe Datei anfordern:** Nutzer hat nur das benannte MicMac-RGB-GeoTIFF ausdrücklich zur Kontrolle freigegeben. Zugriff auf den öffentlichen Drive-Ordner und Abruf dieser Datei waren möglich. Keine allgemeine Freigabe für andere Originale/Flugmetadaten daraus ableiten; Vorschauen/Original bleiben außerhalb Git, Kundenlinks/Koordinaten nicht publizieren.

Das TIFF hat 12.612 × 10.936 Pixel und drei uint8-RGB-Bänder. Eingebettetes CRS und Rastertransform sind vorhanden; das belegt keine richtige Lage oder Dachgeometrie. Die Prüfung umfasste Gesamtansicht und drei native 1.200 × 800-Ausschnitte, keine bloße Dateimetadatenprüfung:

- Oben/mittig und seitlich liegen große Dach-/PV-Stücke mit abrupten Positions-/Maßstabswechseln aneinander; zusammengehörige Kanten setzen sich nicht konsistent fort.
- Auch in schärferen unteren Modulflächen sind Zell-/Modulraster versetzt oder unterbrochen, mit sichtbaren Nahtsprüngen und schwarzen Löchern innerhalb der Dachfläche.
- Ergebnis **FAIL für PV-Modulprüfung/Modul-IDs**, keine geometrische oder fachliche Freigabe. Kein zusätzlicher Abruf der externen RGB-Referenz; direkter Qualitätsvergleich weiterhin offen.
- NoData ist nicht gesetzt, ein Alphaband fehlt und alle drei Bandmasken melden all_valid. Lücken gelten technisch als gültige Rasterpixel. Eine belegte MicMac-Gültigkeitsmaske ist gesondert zu erhalten/übernehmen; **nicht sämtliche schwarzen RGB-Werte automatisch als NoData behandeln**. Diese Metadatenlücke erklärt nicht die sichtbaren geometrischen Fehler.

**180°-Vermutung:** Gegenläufige Flugstreifen sind grundsätzlich photogrammetrisch verarbeitbar. PV-Reflexionen und ähnliche Modulraster können falsche Zuordnungen begünstigen; dies ist hier eine mögliche Erklärung, keine nachgewiesene Ursache. Aus dem Endraster allein lassen sich fehlerhafte Orientierung/Selbstkalibrierung und Fehler der dichten Oberfläche/Orthorektifizierung nicht eindeutig trennen. Kein pauschales Drehen/Spiegeln der JPGs als angeblichen Fix empfehlen.

**Genau nächster technischer Schritt:** vorhandene Ergebnisse im privaten MicMac-Laufordner wiederverwenden: Kameraorientierungen aus Tapas/CenterBascule, vorhandene Qualitätsausgaben und Malt-Oberfläche. Lokal zunächst prüfen, ob Flugstreifen/Kameras geometrisch konsistent angeordnet sind; anschließend Oberfläche/Abdeckung an denselben sichtbaren Bruchstellen beurteilen. Nur die belegte fehlerhafte Standardstufe korrigieren. Noch kein konkreter Orientierungs-/DSM-Fix belegt; keine neue Engine oder erneute vollständige Berechnung. Der bisherige RGB-gestützte Thermal-Kandidat wird bis zur Prüfung dieser RGB-Geometrie zurückgestellt. Thermal-Native-Test nicht wiederholen.

## Historischer Einstieg 02.11.2026: RGB-Datei erhalten, Thermalweg begrenzt prüfen

Die unten beschriebene erste RGB-Sichtprüfung ist inzwischen erfolgt und fehlgeschlagen (siehe oben). Frühere Anleitung als Historie erhalten; nicht wieder als offene Dateianforderung oder Erfolg auslegen.

1. Im privaten Ausgabeordner den Lauf verwenden, dessen Unterordner `thermal` die zuletzt verwendete `step-02.log` enthält. Eine Ebene darüber sollte `rgb_ortho.tif` liegen: Die Anwendung verarbeitet RGB vollständig und prüft dessen GeoTIFF, bevor Thermal beginnt. Datei nicht verschieben/löschen; hier wurde sie nicht unabhängig gesehen oder bewertet. Keine weitere vollständige Berechnung starten, nur um diesen Thermalfehler zu wiederholen.
2. Im vorhandenen Importbereich **„GeoTIFF / GIS-Metadaten prüfen“** dieses RGB-GeoTIFF auswählen. CRS, Rastermaße und Datenmaske lokal prüfen; Ergebnis anschließend in einem vorhandenen lokalen Rasterbetrachter mit der privaten RGB-Referenz auf Modulränder, Doppelkonturen, Nähte und Abdeckung vergleichen. Metadatenprüfung allein ist keine Qualitätsabnahme. Einzelregistrierung als Metadatenartefakt ersetzt kein vollständiges RGB-/Thermal-Paar; zentrale Paaransicht braucht weiterhin beide echten Raster. Keine RGB-Datei als Thermal zuweisen. Dateien und Koordinaten bleiben lokal.
3. Der bisherige unabhängige Thermal-Tapas-Pfad ist an diesem Bestand weiter blockiert. Native-Auflösung hat nicht genügt. Keine Serie zufälliger Modell-/Schwellenwechsel anschließen und keine Bilder still aussortieren. Der Fehler beweist fehlende tragfähige Verbindung zur Initialisierung, benennt aber nicht eindeutig die physische Ursache.
4. Als etablierter Ansatz kommt MicMacs Rigid-Block-Unterstützung für gekoppelte Kameras infrage. Dafür sind eigene Thermal-Intrinsics und relative Rotation/Translation RGB↔Thermal bzw. deren belastbare Schätzung nötig. Gleiche Bildnummern verbinden Aufnahmen, bestimmen diese Geometrie aber nicht. Die geprüften Beispiele beginnen mit vorhandenen Kameraorientierungen; deshalb sind sie **keine unmittelbar ausführbare Lösung** für den aktuellen Abbruch. Vor Codeänderung klären, aus welcher vorhandenen Quelle oder welchem MicMac-Standardverfahren diese Größen für die M3T stammen können. Keine RGB-Kalibrierung kopieren, keine Herstellerwerte raten. Eine externe RGB-Kalibrierungsdatei wird dadurch nicht zur allgemeinen Voraussetzung.

**Öffentliche Quellbelege (nur gelesen, keine Kundenbilder verarbeitet):**

- [MicMac v1.2.0 GraphePose.cpp, Zeilen 247–270](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/Apero/GraphePose.cpp#L247): nicht genügend Initialisierungsverbindungen, Ausgabe UN-Connected und Assert „Connection pb in MST“.
- [Campari-Rigid-Block-Parameter](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/CPP_Campari.cpp): BlocGlob lädt StructBlockCam; keine automatische Gewinnung einer unbekannten Sensorpose allein aus Dateinummern.
- [Offizielles Rigid-Block-Beispiel](https://github.com/micmacIGN/Documentation/blob/master/Data/Rigid-Block/Cmd.txt): bestehende Kalibrierung/Orientierung, danach Blinis und Campari. Beispielkamerawerte niemals auf DJI übertragen.
- [Block-Schätzung aus Initialorientierungen](https://github.com/micmacIGN/Documentation/blob/master/Data/Matis-Img/Stereo-Apero-EstimBlock.xml): BDD_Orient, CalibPerPose und PosFromBDOrient vor EstimateOrientationInitBlockCamera. Kein Beleg einer ohne Thermalorientierung funktionierenden M3T-Kette. Dokumentationslinks auf master können sich ändern; konkrete installierte Windows-Version hier nicht unabhängig bestimmt.

**Abnahme weiterhin offen:** zunächst lokales RGB sichtbar prüfen; für Thermal erst einen belegten Standardweg mit korrekter Sensorgeometrie wählen, anschließend Vollständigkeit aller Thermalorientierungen, GeoTIFF-Abdeckung und RGB-/Thermal-Lage kontrollieren. Keine Orthofoto-/Celsius-/Fachfreigabe aus grüner CI oder einem gestarteten Werkzeug ableiten.

## Vorhandenen Stand verwenden

**Start und Projektladen bestätigt:** Der Nutzer hat die Schritt-115-Startdatei aus Downloads mit vorhandenem Python auf F: ausgeführt; Programm geöffnet und vorhandenes Projekt geladen. Aktualisierung und Projektauswahl jetzt nicht wiederholen. Weiter unten bei „Projekt und MicMac-Lauf“ fortsetzen. [Startanleitung](ZIP_AKTUALISIERUNG_WINDOWS10.md) nur bei späterem Bedarf verwenden.


Windows 10 bleibt. Der Nutzer hat MicMac unter `E:\Tools\MicMac\bin\mm3d.exe` bereits ohne Fehlermeldung gestartet. Installation und diesen Starttest nicht wiederholen. Die vollständige Verfügbarkeit der benötigten Helfer wird erst durch den Bildlauf belegt.

Die aktuelle SolarCheck-Version des bestehenden Branches `feature/orthofoto-license-neutral-rgb-first-20261028` auf dem Auswerterechner verwenden. Vorhandene Projektdatei und importierte Bilder erhalten; nicht erneut importieren oder eine neue Bild-/Archivinventur beginnen. Kein Merge nach `main`. Wenn der neue MicMac-Knopf fehlt, zunächst den lokalen Quellcodestand aktualisieren; das ist kein Anlass, die Funktion neu zu entwickeln.

## Bedienweg in SolarCheck

### Vorhandenen Windows-Starter verwenden

`scripts/start_windows10_offline.ps1` ist bereits vorhanden. Ohne Parameter verwendet es weiterhin `.venv\Scripts\python.exe`. Für ZIP-Aktualisierungen bietet `-UseExistingProject` die Auswahl der vorhandenen SQLite/Python samt lokaler Sicherung vor dem GUI-Start. Es setzt den Quellcodepfad und startet `python -m mcm_solarcheck.offline`. Es installiert nichts und führt keine Bildverarbeitung automatisch aus. Keinen weiteren Launcher bauen.

Die Standardprojektdatei liegt bei diesem Einstieg unter `%USERPROFILE%\MCM-SolarCheck\solarcheck.sqlite3`, unabhängig vom aktuellen Programmordner. Falls der bisherige individuelle Start ausdrücklich eine andere Datenbank übergibt, diesen Startweg beibehalten. Nicht eine neue leere Datenbank als vermeintlich verlorenes Projekt behandeln und die Originale erneut importieren. Der Nutzer hat inzwischen ZIP-Nutzung auf F: bestätigt; den ZIP-Modus des vorhandenen Starters verwenden, keinen zweiten Launcher bauen.

Für einen bestehenden Git-Checkout: SolarCheck schließen und PowerShell im **Programmordner** öffnen (enthält `src`, `scripts` und `.venv`). Der folgende Block aktualisiert ausschließlich den erwarteten Feature-Branch und bricht bei anderem Branch oder lokalen Änderungen ab:

```powershell
$solarCheckBranch = 'feature/orthofoto-license-neutral-rgb-first-20261028'
$solarCheckCurrent = git branch --show-current
if ($LASTEXITCODE -ne 0 -or $solarCheckCurrent -ne $solarCheckBranch) {
    throw 'Bitte zuerst den bestehenden SolarCheck-Feature-Checkout verwenden.'
}
$solarCheckChanges = git status --porcelain
if ($LASTEXITCODE -ne 0 -or $solarCheckChanges) {
    throw 'Lokale Änderungen zuerst prüfen; es wird nichts zurückgesetzt.'
}
git pull --ff-only origin $solarCheckBranch
if ($LASTEXITCODE -ne 0) { throw 'Aktualisierung abgebrochen; bisherigen Stand erhalten.' }
& .\scripts\start_windows10_offline.ps1
```

Bei der bestätigten ZIP-Nutzung diesen Git-Block nicht verwenden; stattdessen [ZIP-Anleitung](ZIP_AKTUALISIERUNG_WINDOWS10.md) und `-UseExistingProject` nutzen. Keine Neuinstallation von MicMac und kein Windows-11-Wechsel erforderlich.

### Projekt und MicMac-Lauf

1. Das vorhandene Offline-Projekt öffnen und zu **Verarbeitung** wechseln.
2. **„RGB- und Thermal-Orthofotos mit MicMac erstellen …“** öffnen. Das Öffnen des Dialogs startet noch keinen Prozess und liest keine Bildpixel.
3. Bei **MicMac-Programm** `E:\Tools\MicMac\bin\mm3d.exe` wählen. Diese Auswahl wird lokal für spätere Starts gespeichert.
4. Einen privaten Ausgabeordner wählen, beispielsweise einen neu angelegten Ordner `E:\SolarCheck-Ausgaben`, getrennt von Originalbildern und Git. Darunter entsteht für jeden Lauf ein frischer Unterordner `micmac-…`; vorhandene Ergebnisse werden nicht überschrieben.
5. Das optionale **Ziel-Koordinatensystem** leer lassen, wenn die tatsächlichen importierten WGS84-Kamerapositionen eindeutig in eine UTM-Zone passen. PROJ wählt dann diese Zone aus seiner CRS-Datenbank. Ein anderes metrisches Zielsystem nur bewusst und mit bekanntem Bezug angeben. Es werden weder Kamerapositionen noch Höhen erfunden.
6. **„Lokal erstellen“** drücken. Erst dieser bewusste Bedienvorgang startet die separat installierte Software. MicMac verarbeitet alle im Projekt importierten RGB- und Thermal-JPEGs, je Sensor getrennt, auf Arbeitskopien. Angezeigt werden Kopierfortschritt und die jeweilige Standardstufe.
7. Nach zwei verwendbaren Ergebnissen übernimmt SolarCheck das Paar gemeinsam in die bestehende Projektregistrierung und öffnet die **Anlagenübersicht**. Überblendung/Zoom prüfen, Projekt schließen und wieder öffnen. Das Paar muss weiterhin erscheinen.

Mindestens drei Bilder pro Sensor mit vorhandener Länge, Breite und Kamerahöhe sind erforderlich. Fehlende Werte werden nicht durch Nullen, eine vermutete Bodenhöhe oder ein geratenes CRS ersetzt. MicMac schätzt Kameraparameter mit `Tapas`; eine extern verifizierte RGB-Kalibrierungsdatei ist keine allgemeine Voraussetzung. Fehlende importierte Kamerapositionen sind eine andere Frage als Kamerakalibrierung.

Die Höhenwerte werden aus dem Import unverändert übernommen; ihr Höhenbezug und ihre Genauigkeit gelten nicht automatisch als unabhängig geprüft. Ein GeoTIFF mit GNSS-Bezug ist kein Vermessungsnachweis. Das Ergebnis bleibt `metadata_only`; keine automatische Review-/Berichtsfreigabe. Thermal ist zunächst Darstellung, keine kalibrierte Celsiusmatrix.

## Lokale Ergebnisse und Fehler

Im neuen Arbeitsordner liegen `rgb_ortho.tif`, `thermal_ortho.tif`, `job.json` sowie getrennte Arbeitskopien und Stufenprotokolle in `rgb/` und `thermal/`. GDAL übernimmt den tatsächlich von MicMac ausgegebenen Rastertransform und seine Masken; ohne brauchbare Georeferenz wird kein CRS-Etikett als Ersatz eingesetzt.

**Abbrechen** beendet die zugehörigen Prozesse und übernimmt kein Teilpaar. Auch Projektwechsel oder Schließen während des Laufs lösen einen Abbruch aus. Bei Fehlern wird kein unvollständiges Paar registriert; lokale Zwischenprodukte/Protokolle bleiben zur Prüfung erhalten. Für einen weiteren Versuch entsteht ein neuer Arbeitsordner.

Wenn eine Standardstufe scheitert, zunächst deren konkrete Meldung und das betreffende lokale Protokoll prüfen. Die GUI nennt Stufe/Fehlercode ohne private Rohprotokolle. Protokolle können GPS/Dateiangaben enthalten und bleiben lokal; keine Kundenbilder, Koordinaten oder produktiven Datenbanken für eine Rückmeldung hochladen. Keine neue Engine oder eigenständige Diagnose-Toolchain als Ersatz beginnen.

## Vergleich mit dem privat bereitgestellten WebODM-RGB-Orthofoto

Der Nutzer hat ein mit WebODM erzeugtes **RGB-Orthofoto** im privaten Google-Drive-Bestand abgelegt. Es wurde hier weder geladen noch verglichen. Den benötigten Referenzdatensatz bewusst auf dem Auswerterechner bereithalten; keine Dateilinks oder Raster nach GitHub/CI/Codex übernehmen. Dies ist ein Vergleich zweier Ergebnisse, keine WebODM-Integration oder Ausführung durch SolarCheck.

Die erzeugte MicMac-RGB-Datei und die RGB-Referenz lokal in vorhandener freier GIS-Software vergleichen, etwa QGIS. Beide tatsächlichen CRS verwenden und geografisch deckungsgleich darstellen. **Die RGB-Referenz nicht als Thermal-Datei in einem SolarCheck-Paar registrieren.**

An denselben bekannten Problemstellen prüfen:

- **Abdeckung:** gesamte Anlage, Ränder und Übergänge zwischen Flugstreifen; keine still ausgelassenen Bilder oder größeren Lücken.
- **Modulschärfe:** native Auflösung/Pixelansicht verwenden, einzelne Modulränder und Zell-/Rahmenlinien beurteilen. SolarChecks begrenzte Gesamtvorschau allein reicht dafür nicht.
- **Geometrie:** Doppelkonturen/Geisterkanten, versetzte Modulreihen und systematische Lageunterschiede suchen.
- **Nähte:** harte Übergänge und Farb-/Helligkeitssprünge beurteilen, besonders an den früher fehlerhaften Streifenübergängen.
- **Lage und Thermal:** CRS, Ausdehnung und tatsächliche gemeinsame RGB-/Thermal-Abdeckung prüfen; gleiche Bildnummern allein belegen keine pixelgenaue Sensorregistrierung.

Die WebODM-Ausgabe ist eine Vergleichsreferenz, keine automatisch fehlerfreie Vermessungswahrheit. Nachweisbare Probleme des aktuellen MicMac-Laufs gezielt an den vorhandenen Standardstufen beheben. VERT-01 ist erst nach echtem lokalem Lauf und fachlicher Prüfung abgenommen. Danach folgt die bereits vorgesehene PV-/Thermal-Befundkette VERT-02.
