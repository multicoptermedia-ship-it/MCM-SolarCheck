# Hummintech – realer RGB-Flugbildbefund vom 28.10.2026

Temporäre ClientError-Zugriffsfehler überwunden. Alle sechs Archive tatsächlich READ-ONLY geöffnet; RGB2.tip ist ein gültiger ZIP-Container.

| Archiv | Fotos | Nummern |
| --- | ---: | --- |
| RGB7.zip | 21 | 0001–0021 |
| RGB6.zip | 26 | 0022–0047 |
| RGB5.zip | 25 | 0048–0072 |
| RGB4.zip | 27 | 0073–0099 |
| RGB2.tip (ZIP) | 28 | 0100–0127 |
| RGB1(1).zip | 33 | 0128–0160 |
| **Gesamt** | **160** | **0001–0160 lückenlos** |

**TATSÄCHLICH GEPRÜFT:** Alle 160 Originalhauptfotos lassen sich als DJI-M3T-WideCamera-RGB 4000×3000 dekodieren. Alle 160 enthalten GNSS, GpsStatus RTK, AltitudeType RtkAlt, Gimbal-/Flight-Ausrichtung, RtkStdLat/Lon/Hgt im DJI-XMP; aus EXIF eines Originals Brennweite 4.4 mm (KB-Äquivalent 24 mm). Relative GNSS-Kameraausdehnung ca. 37.4×51.1 m, 2.02 m mediane Nachbarbilddistanz. Geräteinterne RTK-Std ca. 8–11 mm horizontal und 19–21 mm vertikal, ohne unabhängige Genauigkeitsprüfung. KEINE absoluten GPS-Koordinaten hier enthalten.

Sieben Flugstreifen (0001–0020, 0021–0041, 0042–0066, 0067–0092, 0093–0120, 0121–0148, 0149–0160). Aus echten Bildern über 130 geometrische MERKMALS-KANDIDATEN zwischen aufeinanderfolgenden Streifenfotos. Streifenweise Näherung der Bildskalierung bei 1000-Pixel-Arbeitsbreite zwischen etwa 0.0099 und 0.0114 m je Pixel; KEIN geklärtes tatsächliches Dachhöhenmodell. Solche Differenzen sind Hinweise auf noch zu rekonstruierende Kamera-/Dachebenen, keine freigegebenen metrischen Maße.

**GEOMETRIE NICHT BESTANDEN:** Aus 160 Bildern erzeugte RTK-/2D-gestützte Gesamt-Prüfansicht zeigt Mehrfachkonturen und unscharfe PV-Module in Überlappungen. Einzelstreifen sehen wesentlich besser aus. Gesamtansicht darf NICHT als Orthofoto vermessen, zur Modul-ID-Vergabe oder Thermalprüfung verwendet werden. Nächster Kernschritt: gemeinsames 3D-Kameranetz mit RTK-Priors/BA und reale unterschiedliche Dachflächen, danach Sichtbarkeit + streifenübergreifende Orthorektifizierung und unabhängige Qualitätsprüfung.

Die sechs Archive enthalten 160 RGB-Fotos. Aussage des Nutzers zu 127 Thermalbildern ist in diesem Datensatz noch nicht anhand tatsächlicher Thermalfotos geprüft.

Auf Draft PR #9 neu: rgb_flight_zip_series.py + CLI mit sicherem Multi-ZIP-/auch .tip-Container-Intake, XMP-/JPEG-Lesung ohne Extraktion und privatsphärenschonenden Aggregatberichten. Exakten neuesten CI-HEAD prüfen.

**Vertraulichkeit:** Keine privaten Originalbilder, Roh-EXIF, GPS-Koordinaten oder erzeugten Raster in GitHub gespeichert. Bilder/temporäre Ausgaben existieren in dieser Chat-Arbeitsumgebung, sind in Folgechats nicht automatisch garantiert.
