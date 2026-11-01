# Erster lokaler MicMac-Lauf und Vergleich mit der RGB-Referenz

Stand 01.11.2026 · VERT-01B2 ist technisch angebunden, Code `dd8ed5c1`. **Der tatsächliche Bildlauf auf dem Windows-10-Auswerterechner und seine Fachabnahme stehen aus.** Die Tests nutzen synthetische Bilder und eine Fake-MicMac-CLI; sie prüfen die Anbindung, keine Rekonstruktionsqualität.

## Vorhandenen Stand verwenden

Windows 10 bleibt. Der Nutzer hat MicMac unter `E:\Tools\MicMac\bin\mm3d.exe` bereits ohne Fehlermeldung gestartet. Installation und diesen Starttest nicht wiederholen. Die vollständige Verfügbarkeit der benötigten Helfer wird erst durch den Bildlauf belegt.

Die aktuelle SolarCheck-Version des bestehenden Branches `feature/orthofoto-license-neutral-rgb-first-20261028` auf dem Auswerterechner verwenden. Vorhandene Projektdatei und importierte Bilder erhalten; nicht erneut importieren oder eine neue Bild-/Archivinventur beginnen. Kein Merge nach `main`. Wenn der neue MicMac-Knopf fehlt, zunächst den lokalen Quellcodestand aktualisieren; das ist kein Anlass, die Funktion neu zu entwickeln.

## Bedienweg in SolarCheck

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
