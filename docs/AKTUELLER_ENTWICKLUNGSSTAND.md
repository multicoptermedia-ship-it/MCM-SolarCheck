# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md) und [Produktanforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) lesen. Nutzerentscheidung vom 31.10.2026: zwei extern berechnete Orthofotos, RGB und Thermal.** Neueste Nutzeranweisung hat Vorrang vor älteren Planungen.

## Auftrag und Repository
Für die PV-Anlagenanalyse werden **ein RGB-Orthofoto und ein Thermal-Orthofoto** benötigt. Beide sind zweidimensionale georeferenzierte Raster. Die Berechnung übernimmt etablierte, kostenfreie Open-Source-Software; **keine neue Photogrammetrie-Engine**, kein Nachbau vorhandener SfM-/BA-/Stitch-/Dachalgorithmen in SolarCheck. Eine interne Oberflächenberechnung des externen Programms ist kein Auftrag für eine eigene SolarCheck-3D-Ansicht.

Aktives Repository ist ausdrücklich wieder **`multicoptermedia-ship-it/MCM-SolarCheck`**, bestehender Branch `feature/orthofoto-license-neutral-rgb-first-20261028`, Draft **PR #9**. Diese neue Anweisung ersetzt die frühere Beschränkung auf SolarCheck 2 und den früheren Nur-Lese-Status dieses Repositorys. `mcm-solarcheck2` in dieser Runde unverändert lassen. **Kein Merge und kein Push nach `main`.**

**Keine proprietäre oder kostenpflichtige Software, kein ODM/WebODM/ODX integrieren, aufrufen oder paketieren.** Das bereits vorhandene WebODM darf der Nutzer unabhängig und manuell außerhalb von SolarCheck verwenden; Dateiausgabe und GeoTIFF-Import sind keine Softwareintegration. SolarCheck startet oder installiert es nicht. Windows 10/offline bleibt Ziel. Originalbilder, GPS/RTK-Daten, Kundenprojekte/SQLite, echte Raster und private Analyseergebnisse **nicht nach GitHub, CI oder in Cloud-Dienste übertragen**. Diese Runde verwendet ausschließlich Quellcode, öffentliche Softwaredokumentation und künstlich erzeugte Test-GeoTIFFs. Keine privaten Originaldaten zur Cloud-Berechnung öffnen oder erneut inventarisieren.

## Ausgangsstand und abgeschlossene Forschung
- Ausgangs-HEAD `0aa6171cac10683fc4022a2cfded3b9aff607991`: Python-/Windows-CI unter 3.11/3.12 erfolgreich. [Python](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/41236227496), [Windows](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/41236227490). Spätere Änderungen am exakten neuen HEAD prüfen.
- `main` bei Prüfung unverändert `5f2de8fa47c7ece5b721ca46b9a29c8c5b194059`. PR #7, PR #8 und PR #9 Draft/open/unmerged. Keine Freigabe aus älteren grünen Läufen ableiten.
- Historische Kennung **DEV-RGB-ORTHO-ENGINE-001** bleibt nachvollziehbar. **3D-Entwicklung bis auf Weiteres einfrieren**: alte eigene SfM-/RTK-BA-/Dachvorschauen sind eingefrorene Forschung. `PRIVATE_160_RGB_READONLY_RUN.md` ist kein aktueller Arbeitsauftrag.
- Der frühere echte Windows-10-Mosaiktest war wegen Doppelkonturen, unscharfer Module und Nähten FAIL. Die bereits behobene wiederholte Verzerrung in der kleinen 2–32-Bild-Vorschau belegt keinen Fix des damaligen 160-Bild-Gesamtbilds. Keine weiteren Eigenentwicklungen daran als neuen Orthofoto-Lieferpfad beginnen.

## Freie Werkzeuge: MicMac konkret prüfen
MicMac bleibt ein wichtiges Prüfobjekt, **keine pauschal freigegebene mitgelieferte Toolchain**. Der Kern nennt CeCILL-B; die untersuchte V1-Distribution enthält jedoch gesondert lizenzierte Komponenten, einschließlich Einschränkungen für kommerzielle Weiterverteilung. Nutzungs- und Weiterverteilungsrecht unterscheiden; nicht aus der Hauptlizenz eine Freigabe aller Binärbestandteile ableiten. Keine ungeprüfte Distribution automatisch installieren, bündeln oder als vollständig freie Integration bezeichnen.

Geprüfte öffentliche Quellen, Versionsstand, Windows-/Offline-Eignung, Alternativen und Thermalgrenzen: [FREIE_ORTHOFOTO_WERKZEUGE.md](FREIE_ORTHOFOTO_WERKZEUGE.md). Praktischer Importweg: [EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md). **Keine proprietären Testlizenzen oder SDKs als Ausweichweg.** QGIS/GDAL können vorhandene Georeferenzierung übernehmen/reprojizieren; aus Foto-GPS allein entsteht kein Dachorthofoto. Kein EPSG erfinden.

## Bestehenden GeoTIFF-Weg erweitern
SolarCheck besitzt bereits GeoTIFF-Prüfung, Projektregistrierung und GIS-basierte RGB-/Thermal-Überblendung. Diese Funktionen werden wiederverwendet; kein neuer Bildimporter und keine neue Rechenengine.

Umgesetzt im aktuellen Integrationsblock:
1. Zwei lokale GeoTIFFs nach expliziter RGB-/Thermal-Rolle gemeinsam prüfen und atomar in Schema 22 speichern. Herkunft und Thermal-Darstellung beziehungsweise Rohwerte werden getrennt erfasst; Registrierung bleibt `metadata_only`, keine fachliche Freigabe.
2. Unterschiedliche CRS/Auflösungen über den vorhandenen Rasterio-Weg ausrichten. NaN-NoData und GDAL-/Alpha-Masken beider Raster beachten. Ein komplett ungültiges RGB darf keine gemeinsame Abdeckung vortäuschen; Thermal-Falschfarben nicht als Band-1-Messwert behandeln.
3. Vorhandene PV-Detektoren auf begrenzte RGB-GeoTIFF-Fenster anwenden und Modulpolygone über tatsächliche CRS/Affine in das Thermal-Raster zuordnen. Vorschläge bleiben zur Prüfung; kein neuer Detektor und keine fingierte Originalbild-Homografie.
4. Paarimport, gespeicherte Paare und einen visuellen Bereichswähler für PV-Modulvorschläge im bestehenden Offline-Desktop anbieten. Quellen bleiben unverändert; Rasterzuordnung ist keine Temperatur- oder Vermessungsfreigabe.

Falschfarben, ein Temperaturpunkt und Rohsensorwerte ergeben **keine vollständige kalibrierte Celsiusmatrix**. Geometrische Zuordnung und Temperaturauswertung getrennt behandeln; vorhandene Thermalparser und Erkenntnisse wiederverwenden. Erst belastbare RGB-Modulvorschläge und korrespondierende Thermalflächen, danach nachvollziehbare Befunde und Berichte.

## Validierung und Übergabe
**Abschlussprüfung 01.11.2026:** lokale Gesamtsuite **4.113 bestanden, 15 erwartete Skips, 45 Warnungen in 129,68 s**; `pip check` und Offline-Desktop-Smoke erfolgreich. Der Windows-Workflow führt die neuen Paar-, Masken-, PV-/Thermal-, GUI-, Migrations- und Freigabetests explizit aus. Die CI am exakten Abschluss-HEAD separat prüfen; ältere grüne Läufe gehören zu ihren jeweiligen Commits.
Neue Funktionen werden ausschließlich mit synthetischen Rastern und temporären SQLite-Projekten geprüft. Eine bestehende Berichtsfreigabe bindet die gespeicherten Paarrollen ein; neue oder geänderte Paarinterpretation ist erneut zu prüfen. Die GIS-Zuordnung berücksichtigt Pixelzentren sowie unterschiedliche CRS/Auflösungen, statt einen Halbpixelversatz einzuführen. Noch kein neuer echter RGB-/Thermal-Orthofoto-Lauf auf dem Kundenrechner, keine bestätigte MicMac-Installation, keine reale Windows-10-Fachabnahme. Keine Orthofoto-/PV-/Thermal-/Berichtsfreigabe aus CI allein.

Nach jedem Block zuerst diesen Checkpoint (1.000–8.500 Zeichen), danach [DEVELOPMENT_STEP_REGISTER.md](DEVELOPMENT_STEP_REGISTER.md), [DEVELOPMENT_AGREEMENT.md](DEVELOPMENT_AGREEMENT.md), [CHAT_HANDOFF.md](CHAT_HANDOFF.md) und [PV_ORTHOMOSAIC_FIRST_ROADMAP.md](PV_ORTHOMOSAIC_FIRST_ROADMAP.md) synchronisieren. Exakten Abschluss-HEAD, Tests und tatsächliche Grenzen festhalten. Nächster Praxistest mit Originaldaten ausschließlich lokal außerhalb von Cloud-/GitHub-Zugriff.
