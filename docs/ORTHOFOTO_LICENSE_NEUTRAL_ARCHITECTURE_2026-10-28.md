# Verbindliche Architekturentscheidung 28.10.2026 – Lizenzneutrale Orthofoto-Engine in SolarCheck

## Entscheidung des Anwenders
**Kein ODM, WebODM oder ODX in der Anwendung.** Die Systeme dürfen als allgemeine
Verfahrensreferenz (Arbeitsablauf/Problemklassen) dienen. Keine Übernahme von
Quelltext, Komponenten, Binärdateien, Containern, Serverdiensten, APIs,
Modellgewichten oder lizenzpflichtigen Algorithmen aus diesen Projekten.
Kein verdeckter Start externer ODM/ODX-Prozesse.

Nur eigenständig entwickelte SolarCheck-Funktionen und separat lizenzgeprüfte
technische Abhängigkeiten verwenden; Lizenzen und Abhängigkeiten einschließlich
transitiver/native Komponenten vor Integration dokumentieren. Der Nutzer hat
keine Lizenz- oder Installationsfreigabe für zusätzliche Produkte erteilt.
Fachlich bekannte photogrammetrische Verfahren sind keine Berechtigung,
fremden Programmcode zu kopieren.

## Produktziel und Reihenfolge (RGB first)
**Projekt -> ganze verfügbare RGB-Flugbildserie -> echte photogrammetrische
Rekonstruktion -> RGB-Orthofoto + 3D-Oberflächengeometrie -> fachlich geprüfte
Dach-/Modulflächenansichten -> PV-Modulgrenzen/IDs -> registrierte Thermalwerte
und Befundprüfung.**

Die bisherigen RGB-Paarvorschauen sind ausschließlich Diagnostik.
Aus Match-Inliern, Canvas-Belegung oder einer Homografie allein darf keine
Vermessungs-/Orthofotofreigabe abgeleitet werden. Die bekannten 33 RGB-Bilder
sind nur ein Teilbestand der Befliegung; keine Aussage über fehlende originale
RGB-/Thermalpartner oder vollständige Dachabdeckung.

## Technische Umsetzung, auf bereits vorhandenem SolarCheck-Code
1. Vorhandene projektgebundene Import-/Bildlisten und lokales RGB-Staging
   vollständig **lizenzneutral** wiederverwenden. Die vorhandene Datei
   `services/odm_rgb_adapter.py` führt nach Codeprüfung ausschließlich
   eigenes Scan-/Datei-Staging aus und startet keine externe ODM-Engine.
   Die Namensgebung wird bei nächster relevanter Codeänderung auf
   `rgb_photogrammetry_staging.py` umgestellt, nach Regressionstests mit
   rückwärtskompatibler Behandlung bestehender Aufrufe. Kein neues ODM-Staging.
2. Vorhandene Matcher, Überlappungsgraphen und DJI-Metadaten als Eingaben für
   eine **globale Mehrbildrekonstruktion** verwenden: dauerhafte Merkmals-
   Tracks, Kamera-Intrinsics/Distortion, globale Kameraposen und gemeinsame
   Ausgleichung (Bundle Adjustment), Geometrie-/Kontrollpunktresiduen,
   Flugbandsprünge, Ausreißer und Lücken dokumentieren. Bildpaare sind
   interne Teilrechnungen, nicht das sichtbare Endprodukt.
3. Geeignete 3D-Dachoberflächen / ein überprüftes Oberflächenmodell für
   echte Orthorektifizierung bereitstellen; vorhandene
   `rgb_surface_tiles`, `rgb_surface_tile_render`,
   `rgb_surface_tile_mosaic`, `rgb_surface_mosaic_audit`,
   `rgb_surface_pilot_run` als kachelbegrenzten Renderpfad nutzen.
   Eine horizontale Übersicht und flächenparallel entzerrte Ansichten
   geneigter Module sind **unterschiedliche Produkte**. Dachneigungen
   werden nicht pauschal angenommen.
4. Sichtbares Ergebnis in der vorhandenen Windows-10-GUI: RGB-Raster plus
   gültige Coverage-Maske, ungeklärte Verbindungsbereiche, Naht-/Kontroll-
   punktfehler, Provenienz und klare Statusgrade; vorhandene GeoTIFF-
   Inspektion nur mit nachgewiesenem CRS, GCP/RTK/Survey-Gate.
5. Erst aus diesen geprüften Raster-/Flächenprodukten Haus, Dach, PV-Anlage,
   physische PV-Module und prüfbare Modulpolygone/IDs ableiten. Frühere
   Einzelbilddetektoren bleiben unterstützende Vorschläge, nicht
   freigegebene Modulzählung. Thermal: später radiometrische Rohwerte
   über die nachgewiesene Geometrie zu Modulen zuordnen; kein Temperatur-
   /Defekt-/Berichtsgate automatisch öffnen.

## Der nächste kleine VERTIKALE Implementierungsschritt
**DEV-RGB-ORTHO-ENGINE-001 (geplant):**
Aktives Testprojekt -> **alle** importierten verfügbaren RGB-Primärbilder ->
lokales begrenztes Mehrbild-/Track- und Kameranetz-Processing ->
reproduzierbarer Qualitäts-/Sperrstatus und **erste zusammenhängende
RGB-Dachabschnittskachel**, ausschließlich sofern belastbare 3D-Geometrie
für die Projektion vorliegt. Andernfalls sichtbarer begründeter Sperrstatus,
nicht ein pseudo-metrisches Bild.

Vorhandene Module und CI-Tests zuerst integrieren; neue algorithmische
Pakete nur nach Lizenz-, Windows-10-, Offline-, Ressourcen- und
Datenschutzprüfung. Ausgaben nur in eigenem Test-Arbeitsverzeichnis.
Keine Original-, Produktions-/Test-SQLite-, Backup- oder
`main`-Änderungen ohne ausdrückliche Freigabe.
Keine falsche Behauptung, ein vollständiges Orthofoto sei schon fertig.

## Realer Pilotbefund und offene Altzweige
SC-0003/Hummintech3: Windows-10-Pfad für zwei RGB-Vorschaufotos funktioniert;
0128+0129 zeigte 473 Inlier / 97,8 % Fläche, aber sichtbaren harten
Versatz. Diese qualitativ unzureichende Vorschau ist **kein** Orthofoto.
PR #7 (Nahtdiagnose) und PR #8 (kontrollpunktgebundene Dachflächenkachel)
bleiben getrennte Entwürfe ohne automatische Übernahme. Nur ihre
wiederverwendbaren Bausteine einplanen; keine weitere Optimierung
der reinen Zwei-Foto-Vorschau als Hauptziel.

## Status
Architekturentscheidung und Arbeitsauftrag, **keine** neue funktionsfähige
Photogrammetrie-Engine, keine zusätzliche Drittsoftware installiert,
keine lokale Windows-Hardware oder Originaldaten verändert.
