# Lokale Orthofotos → bestehender GeoTIFF-Import → PV und Thermal

**Nutzerentscheidung vom 31.10.2026:** Je ein Orthofoto aus den RGB- und Thermalaufnahmen bereitstellen. Dafür etablierte freie Programme verwenden, keine eigene Photogrammetrie-Engine und keine proprietäre/kostenpflichtige Software. ODM, WebODM und ODX bleiben als SolarCheck-Integration ausgeschlossen. Das vorhandene WebODM darf der Nutzer unabhängig und manuell außerhalb von SolarCheck benutzen; kein Start/Installer/API/Container aus der App. Zuerst [AKTUELLER_ENTWICKLUNGSSTAND.md](AKTUELLER_ENTWICKLUNGSSTAND.md) lesen.

**Neuer Praxisstand 04.11.2026:** Bisherige MicMac-Kette nach zwei unbrauchbaren Ergebnissen zurückgestellt, darunter abgeschlossener RGB-/Thermal-Lauf einer zweiten Dachanlage mit RTK laut Nutzer. Vorhandenen Import/Viewer erhalten; freie Alternative vor neuer Anbindung lokal qualifizieren. COLMAP/OpenMVS/GDAL ist ein Kandidat, noch ohne Windows-10-/GeoTIFF-/Thermal-Realnachweis. Keine neue Engine oder ODM/WebODM/ODX-Anbindung. Historische MicMac-Anleitung unten ist kein aktueller Auftrag für weitere Parameterläufe.

## Aufgabe von SolarCheck

Die vorhandenen Funktionen **„GeoTIFF / GIS-Metadaten prüfen“** und **„GeoTIFF dauerhaft im Projekt registrieren“** wiederverwenden. SolarCheck übernimmt die beiden lokal erzeugten Raster, ihre Projektzuordnung und anschließend PV-Modulerkennung sowie Thermal-Zuordnung. Kein neuer Importer, kein Nachbau von SfM, Bundle Adjustment, MVS oder Orthorektifizierung.

RGB und Thermal sind getrennte Artefakte. Gleiche Bildnummern verbinden Originalaufnahmen, ersetzen aber keine geometrische Registrierung der Sensoren. Unterschiedliche Rasterauflösungen sind zulässig; CRS, Lage und tatsächliche Überdeckung müssen zusammenpassen.

## Lokaler Ablauf

Derselbe obere Importknopf bietet jetzt auch JPG-Originalaufnahmen: zuerst alle RGB-JPGs, danach alle Thermal-JPGs auswählen; sie werden gesammelt über den vorhandenen Originalbildimport gespeichert. Für bereits fertige Orthofotos je ein GeoTIFF pro Sensor wählen. JPG und GeoTIFF getrennt importieren; gemischte Auswahl wird nicht teilweise übernommen.

Der konkrete, manuell anzupassende MicMac-Weg steht in [MICMAC_LOKALER_RGB_THERMAL_ABLAUF.md](MICMAC_LOKALER_RGB_THERMAL_ABLAUF.md). In SolarCheck führt **Verarbeitung → „Extern erstelltes RGB-/Thermal-Paar übernehmen“** zum vorhandenen Paarimport. Zusätzlich startet „RGB- und Thermal-Orthofotos mit MicMac erstellen …“ die separat installierte MicMac-Version nach bewusster Konfiguration/Bedienaktion. Die fertigen Raster gehen automatisch in denselben Paarimport; [lokaler Erstlauf und Referenzvergleich](MICMAC_SOLARCHECK_LOKALER_TEST.md) stehen noch aus. Der frühere GUI-Knopf für die eingefrorene eigene Erzeugung ist entfernt.

1. Originalbilder, GPS/RTK und Kundendaten auf dem Rechner des Nutzers belassen. Originale nur lesen; externe Verarbeitung ausschließlich in einem getrennten lokalen Arbeits-/Ausgabeordner. Keine Übertragung nach GitHub, CI oder Cloud-Diensten. Entwicklungstests verwenden synthetische Raster.
2. Mit einem etablierten, für die konkrete Zusammenstellung geprüften freien Werkzeug RGB- und Thermal-Orthofoto erzeugen. Auswahl und MicMac-Prüfstand stehen in [FREIE_ORTHOFOTO_WERKZEUGE.md](FREIE_ORTHOFOTO_WERKZEUGE.md). MicMac ist separat installiert; die Anbindung hat bei der zweiten Dachanlage beide Raster erzeugt und angezeigt, die Bildqualität ist jedoch unbrauchbar. Dieser Weg ist zurückgestellt. Eine andere freie Kette muss vor neuer Anbindung lokal qualifiziert werden.
3. Beide GeoTIFFs prüfen: eingebettetes CRS, Rastertransform, Ausdehnung, Pixelgröße, gültige Datenmaske/NoData und Bandbedeutung. Eine `.tif`-Endung allein genügt nicht. Bei TIFF mit Worldfile erst die tatsächliche Koordinatenreferenz feststellen; keinen EPSG-Code erfinden. GDAL/QGIS können bekannte Referenzen übernehmen oder reprojizieren, aber keine fehlende Kamerageometrie durch ein CRS-Etikett erzeugen.
4. Im bestehenden Importbereich **„RGB- und Thermalbilder gemeinsam importieren (JPG / GeoTIFF)“** wählen und beide Sensorrollen eindeutig belegen. Die Transaktion speichert entweder beide Dateien samt Paarzuordnung oder nichts. Thermal als Darstellung oder Rohwerte kennzeichnen, keine Temperaturkalibrierung erfinden. Das gespeicherte Paar erscheint auch in der **Anlagenübersicht → Orthofotos** mit Paarauswahl, Überblendungsregler und Zoom. Im Nachbarreiter bleiben die vorhandenen Modulbeobachtungen erhalten. Nach Projektneustart wird das Paar ohne erneuten Import geladen; bei fehlender Datei zunächst den lokalen Pfad wiederherstellen und „Anlagenübersicht aktualisieren“ wählen. Auswahl/Slider/Zoom ändern keine Quellpixel oder Freigaben.
5. **„PV-Modulvorschläge im RGB-Orthofoto prüfen“** öffnen, mit der Maus einen begrenzten Ausschnitt markieren und den vorhandenen Detektor starten. Die Vorschläge bleiben zur Fachprüfung. Ihre Lage wird über CRS/Affine auf Thermalpixel übertragen; Überdeckung/NoData und Pixelzentren werden berücksichtigt. Noch keine automatisch bestätigten Modul-IDs oder Temperaturbefunde.
6. Modulränder, Doppelkonturen, Nähte und sensorübergreifende Lage am lokalen Ergebnis prüfen. Erst ein echter Vergleich kann die früheren schlechten Nähte des 160-RGB-Piloten fachlich ablösen. Synthetische Tests sind kein Orthofoto-Qualitätsnachweis.

## Thermal: Darstellung und Temperaturwerte unterscheiden

Ein farbiges Thermal-JPEG/GeoTIFF dient zunächst der Darstellung. Numerische Modulbefunde brauchen ein nachweislich radiometrisches Raster mit bekannten Einheiten, Skalierung/Offset und NoData. Den bereits untersuchten mittigen Temperaturpunkt und vorhandene Erkenntnisse wiederverwenden; daraus keine vollständige Celsiusmatrix ableiten.

RGB- und Thermalkamera haben eigene Intrinsics, Verzeichnung und Auflösung. Wiederverwendung einer RGB-Oberfläche durch ein externes Werkzeug setzt eine passende Sensorregistrierung voraus; RGB-Kameraparameter nicht ungeprüft auf Thermal kopieren.

MicMac `Tawny` aktiviert radiometrischen Ausgleich standardmäßig. Für numerische Temperaturdaten `RadiomEgal=0` verwenden; zusätzlich Datentyp, Resampling, NoData und Werteerhalt durch die gesamte Verarbeitung prüfen. Die Option ist keine radiometrische Freigabe. [Quellbeleg v1.2.0](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/uti_phgrm/CPP_Tawny.cpp).

## MicMac: technischer Kandidat, konkrete Toolchain noch nicht freigegeben

MicMac ist ein etabliertes IGN-Projekt mit CeCILL-B-Hauptlizenz und dokumentiertem Windows-10-Build. `Malt Ortho` und `Tawny` sind vorhandene Standardwerkzeuge. Ihre internen Oberflächenberechnungen gehören zum externen Werkzeug; SolarChecks Analyseprodukt bleibt ein zweidimensionales Raster.

Eine pauschale Freigabe der gesamten v1.2.0-Distribution wäre unzutreffend: Der Quellbaum enthält abweichende Bedingungen für ältere SiftPP-Helfer und Shewchuk/Triangle; Letzteres steht im regulären `libelise`-Build. Nutzung und Weiterverteilung unterscheiden. MicMac wird dadurch nicht insgesamt als proprietär bezeichnet; die vollständig freie konkrete Toolchain ist aber noch nicht belegt. **Keine ungeprüften Binärpakete bündeln, automatisch installieren oder als freigegebene Laufzeit anbinden.** Primärquellen und Alternativen: [Werkzeugprüfung](FREIE_ORTHOFOTO_WERKZEUGE.md).

Hier wurden öffentliche Quellen geprüft, keine Kundenbilder verarbeitet und kein MicMac-Windows-/Gesamtfluglauf ausgeführt. Noch keine neue Orthofoto-, Temperatur- oder Vermessungsfreigabe. Kein Merge nach `main`.
