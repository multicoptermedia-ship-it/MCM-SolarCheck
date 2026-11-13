# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md), [Anforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) und [Werkzeugprüfung](FREIE_ORTHOFOTO_WERKZEUGE.md) lesen. Neueste Nutzeranweisung hat Vorrang.**

## Auftrag und Grenzen
Benötigt werden **ein RGB-Orthofoto und ein Thermal-Orthofoto**, georeferenziert als zweidimensionale GeoTIFFs, danach PV-Modulprüfung und Thermal-Zuordnung. Bewährte freie Standardsoftware verwenden; **keine neue Photogrammetrie-Engine**, kein eigener SfM-/BA-/Stitch-/Dachalgorithmus. Externe Programme dürfen intern Oberflächenmodelle berechnen.
Aktiv: `multicoptermedia-ship-it/MCM-SolarCheck`, Feature-Branch `feature/orthofoto-license-neutral-rgb-first-20261028`, Draft **PR #9**. Nutzer hat frühere Nur-Lese-Sperre aufgehoben. SolarCheck 2 unverändert lassen. **Kein Merge/Push nach `main`.**
**Windows 10 bleibt verbindlich.** Offline zuerst, Online danach mit gemeinsamem Python-Fachkern. Keine proprietären/kostenpflichtigen Orthofotoprogramme; Nutzer-Ausnahme 07.11.: Microsoft-C++-Buildtools/SDK nur für OpenSfM-Build. Keine ODM/WebODM/ODX-Anbindung, Prozesse, APIs, Container oder Paketierung. Eigenständiges manuelles WebODM außerhalb SolarCheck bleibt erlaubt; echte GeoTIFFs können über den vorhandenen Import übernommen werden.
Originalbilder/GPS/RTK/Kundendaten/produktive SQLite/Backups/private Raster nicht in GitHub/CI/Codex/Cloud verarbeiten. Standardmäßig nur Quellcode/synthetische Tests; keine autonome ZIP-/EXIF-/ORB-Inventur. Echte Verarbeitung nur lokal nach bewusstem Nutzerstart, Arbeitskopien außerhalb von Originalen/Git; Originale read-only. Gezeigte Screenshots sind keine Erlaubnis zum Laden weiterer Originalarchive.
**DEV-RGB-ORTHO-ENGINE-001: 3D-Entwicklung bis auf Weiteres einfrieren.** Eigene Photogrammetrie bleibt eingefroren. Keine ausdrückliche Wiederaufnahme angeordnet. Offline zuerst, gemeinsame Fachlogik für Online erhalten.

## Vorhandene Teile – nicht erneut bauen
- **DEV-EXTERNAL-ORTHOPHOTO-PAIR-001:** Schema22, GeoTIFF-/GIS-Prüfung, atomare RGB-/Thermal-Paare, PV-Vorschläge/GIS-Zuordnung. metadata_only/Rohwerte/Falschfarben ohne Fach-/Celsiusfreigabe.
- **VERT-01A a4d1e941:** zentrale Rasterübersicht, Paarauswahl, Überblendung/Zoom, Wiederöffnung/Projektwechsel; Modulbeobachtungen eigener Reiter.
- **VERT-01B1 1a9d0c31:** vorhandener manueller Paarimport → Anlagenübersicht, eigene Erzeugung eingefroren.
- **VERT-01B2 dd8ed5c1:** MicMac → GeoTIFF-Paar → Übersicht technisch vorhanden, nach Qualitätsfehlschlag zurückgestellt, Code erhalten.
F:-Python/SQLite/ZIP-Start gemäß AGENTS erhalten. Historische Technik920ba8f2 Linux/Windows inkl.Tk grün; keine Bildabnahme.

## Nutzerbefund und Priorität
**MICMAC-REAL-02 FAIL:** zwei unbrauchbare Praxistests, zweite Dachanlage mit RTK laut Nutzer. MicMac/RGB-POSE-01 zurückgestellt; keine neuen Parameter-/Maskenläufe. Kein generelles Urteil über MicMac.
**ALT-ORTHO-01:** Nutzer bestätigt lokalen COLMAP/OpenMVS-Pilot. 287er-Fortsetzung am 07.11. ohne einzelne Kameralösung beendet, Pilot zurückgestellt; keine Haupt-GUI-Anbindung. Keine neue Engine oder private Original-/DB-Verarbeitung hier.

## Konkreter nächster Einstieg – 13.11.2026 Thermal auf vorhandener Basis
**OPEN-SFM-REVIEW-01:** v1.1/8b6b77ef mit eigenem RGB-GeoTIFF-Weg; [Quellen](OPENSFM_PRUEFUNG_2026-11-07.md). Keine eigene Engine/run_all.bat.
**Setup/GPU geschlossen:** E:\SolarCheck-OpenSfM\env/Python3.10.22/v1.1-8b6b77ef/9native Module; C++17/SDK/x64/MX2502047MiB PASS. NVIDIA582.78/Neustart und C28GB/Cleanup erledigt. Keine Installation/Diagnose; QGIS/Profile/Arduino/F:-Python/SQLite erhalten.
**RGB-REAL-02 Historie:**287/287 RGB/1 Modell/137425 Punkte,7 Anfangsstufen PASS; erste Tiefenkarten nach3600,219 s Stufenlimit beendet, Gesamt5960,282 s. Nicht erneut kopieren/Sparse/Entzerrung/Cluster rechnen; alte COLMAP-Berichte nicht vermischen.
**RUN-IDENTITY-01/CACHE-CHECK-FIX1 geschlossen:** Zeit-/Engine-/Projektordner/sichere Kennzahlen; Legacy lesbar/COLMAP abweisen. .JPG/.JPG.jpg aus gespeicherter Zuordnung; zuletzt43/43Cluster/272clean/22raw. Keine weitere RGB-Diagnose.
**DENSE-RESUME-01 real PASS/RGB-SICHT-01 positiv13.11.:** letzter Versuch finished/1936,110s, orthophoto_created true/7Anfangsstufen wiederverwendet/287clean/0raw; vorher43/43Cluster/272clean/22raw. Gesamtlaufzeit unbekannt, oberes failed bleibt Erstlaufhistorie. Nutzer bestätigt sauberes RGB, Datei undistorted/depthmaps/ortho.tif erhalten/nicht neu rechnen. Unabhängige Geometrie/Lage, Thermal/Temperatur offen; noch kein fertiges Paar.
**SITE-TYPE-01 angefordert/nicht implementiert:** Flächen-/Dachwahl speichern, Standardwerkzeug je Art qualifizieren; [REQ17/18](ANFORDERUNGEN_ORTHOFOTO_CODEX.md). FDach noch ungeprüft, kein belegter OpenSfM-Dachfehlschlag; keine ungeprüfte Dach→Stitch-Automatik. Nach Thermal fortsetzen.
**THERMAL-REFERENCE-01 geschlossen:** separates altes Thermal verzerrt; nicht mit aktuellem Projekt vermischen/keine Drive-/PNG-Suche.
**THERMAL-BASE-01 vorhanden:** [Prüfstand](THERMAL_PRUEFSTAND_2026-11-13.md): historisch242/242 M3T/640×512×16Bit/655360 APP3-Bytes; Parser/Rohwertanalyse/Tests wiederverwenden. Mittiger Messpunkt laut Nutzer früher untersucht, Kontrollreferenz erhalten; vollständige Pixel-°C-Konvertierung im Branch nicht belegt, Provider Stub. Keine neue Originalinventur/Kalibrierdatei-/SDK-Frage.
**THERMAL-SPARSE-BRIDGE-01 aktueller Einstieg:** Nutzerlauf13.11./18:58:37/oh9ptgy5:287 Thermal/Rohdaten akzeptiert,595,094s. Teilmodelle280Bilder/70468Punktdatensätze,3/733,2/84;2 fehlen. Keine gemeinsamen Bilder; nur5 gemeinsame Punkt-IDs zwischen0/1, sonst0. Summe71285 enthält Mehrfachzählungen; Standardmerge braucht≥10 geometrische Inlier und ist damit nicht möglich. Kein Dense/Orthofoto. Komponentenprüfung abgeschlossen; keine neue Rohdaten-/GPU-/Importprüfung.
Neuer einmaliger Zusatzabgleich implementiert: Ausgangslauf erhalten, getrennte bytegeprüfte Arbeits-/Metadaten-/Feature-/Matchkopien. Nur7 Außenbilder als native OpenSfM-Referenzmenge gegen alle287: maximal1981Paare inklusive Außenbilder untereinander. Bereits gespeicherte Paare beider Richtungen (auch leere) überspringen/erhalten. Standard-pairs_selection/match_images_with_pairs/DataSet-Lader, keine eigene Matching-/SfM-/Merge-Engine, keine gelockerten Schwellen/RGB-Posen. Metadaten/Features nicht neu rechnen/keine neue Raw-Inventur. Neue Tracks/Rekonstruktion; nur1 vollständiger endlicher287er Verbund mit eigener Thermalgeometrie darf gleiche Standard-Dense-/GeoTIFF-Kette fortsetzen. Ohne neue robuste Matches/unvollständig stoppen, keine Wiederholung/Teilfreigabe. Quellenlock/Marker1Versuch; alte Dateien erhalten. max60min/Stufe/3hgesamt, eigener Prozessabbruch. Quelle29eb9c99 alle drei CI grün/Windows43486193637 (3.11/3.12/Tk); ZIP/zehn Codeeinträge geprüft. Nächster Nutzerweg neuer Thermal-Dialog → Lauf laden/18:58:37/oh9ptgy5 → Zusatzabgleich starten → neue Kennzahlen/gegebenenfalls Sichtprüfung. Kein neuer normaler Bildlauf/Dense-Resume für alte Teilmodelle. Danach vorhandener Paarimport/RGB-Überblendung/PV/KI/Review; Dach danach.


Abnahme: vollständige Dach-/PV-Flächen, scharfe zusammenhängende Modulränder, keine versetzten Stücke/Doppelkonturen, belegte Georeferenz, vertretbare gemessene Laufzeit, anschließend räumlich passendes Thermal. Danach vorhandene PV-/Thermal-/Review-/Berichtskette verbinden. **VERT-01 insgesamt fachlich weiterhin nicht abgenommen; aktueller RGB-Datensatz technisch und in erster Nutzersicht positiv.**

## Frühere Befunde – nicht wiederholen
26/26-Serie ohne RTK separat: RGB/Thermal FAIL. PNG-/Cache-/GrShade-/Dateisuche abgeschlossen; nicht wiederholen. Details im Register.

## Verbindliche vertikale Chat-Übergabe
Start: AGENTS, Checkpoint, Anforderungen/Register lesen; lokalen/Remote-HEAD und exakte CI prüfen. Am genannten offenen Teil fortsetzen, keine geschlossenen Funktionen erneut bauen.
Ende: zuerst diesen Checkpoint (1.000–8.500 Zeichen), dann Register/Vereinbarung/Handoff/Roadmap aktualisieren: Block-ID/Status, Commit/Testbelege, offene Lücke, genauer nächster Einstieg und Abnahme. Quellenprüfung, technische Tests und reale Fachabnahme getrennt kennzeichnen. CI allein ist keine Produktfreigabe. Praxis-PDF-Profil bleibt verbindlich; Original-PDFs nicht nach Git. VERT-02/Befund→Modul-ID→RGB-Vergleich→gespeicherte Entscheidung→Bericht danach; Online/Zahlung/Installer nachrangig.
