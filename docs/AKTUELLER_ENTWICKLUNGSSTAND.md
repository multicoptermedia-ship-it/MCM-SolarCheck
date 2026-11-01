# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md) und [Produktanforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) lesen. Nutzerentscheidung vom 31.10.2026: zwei extern berechnete Orthofotos, RGB und Thermal.** Neueste Nutzeranweisung hat Vorrang vor älteren Planungen.

## Auftrag und Repository
Benötigt werden **ein RGB-Orthofoto und ein Thermal-Orthofoto**, zweidimensional und georeferenziert. Etablierte kostenfreie Open-Source-Software übernimmt die Berechnung; **keine neue Photogrammetrie-Engine**, kein eigener SfM-/BA-/Stitch-/Dachalgorithmus.
Aktiv: **`multicoptermedia-ship-it/MCM-SolarCheck`**, Branch `feature/orthofoto-license-neutral-rgb-first-20261028`, Draft **PR #9**. Die frühere Nur-Lese-Sperre ist aufgehoben. SolarCheck 2 unverändert lassen. **Kein Merge/Push nach `main`.**
Windows 10/offline zuerst. Keine proprietäre/kostenpflichtige Software und keine ODM/WebODM/ODX-Anbindung, Ausführung oder Paketierung durch SolarCheck. Eigenes WebODM bleibt ausschließlich manuell außerhalb der App zulässig. Kundenbilder/GPS/RTK/SQLite/echte Raster nie in GitHub, CI oder Cloud übertragen; nur Quellcode und synthetische Tests lesen. Keine private Rohbildinventur oder autonome Bildöffnung.

## Gesicherte Basis
Letzter abgeschlossener Codeblock: **VERT-01A**, Code-Commit `a4d1e9410865240a4866092d510cdbb16fb6fd62`. Lokale Gesamtsuite: **4.121 bestanden, 15 Skips, 76 Warnungen (163,65 s)**; acht vertikale Tests nach abschließender Testpräzisierung separat grün. Vorgänger `d75459e9`: sechs grüne CI-Jobs bestätigt (Linux Push/PR und [Windows PR](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/41329796339)). Neue HEAD-CI nach Push gesondert prüfen; alte Läufe sind kein Nachweis neuer Änderungen.
Historische Kennung **DEV-RGB-ORTHO-ENGINE-001**: **3D-Entwicklung bis auf Weiteres einfrieren**. Eigene SfM-/BA-/Stitch-/Dachforschung ist eingefroren und kein Lieferpfad. Der frühere reale Windows-10-Gesamtmosaiktest bleibt FAIL. Kein erneuter Forschungs-/Inventurstart.

## Vorhandene Funktionen und Grenzen
**DEV-EXTERNAL-ORTHOPHOTO-PAIR-001 ist technisch umgesetzt:** vorhandene GeoTIFF-Prüfung/Registrierung um atomare RGB-/Thermal-Paare in SQLite-Schema 22 erweitert; Rollen/Herkunft, Masken/Alpha/NaN-NoData und unterschiedliche CRS/Auflösungen geprüft. Der vorhandene PV-Detektor arbeitet auf gewählten RGB-Fenstern und ordnet Polygone über CRS/Affine mit korrekten Pixelzentren dem Thermalraster zu. Importseite bietet Paarregistrierung, Wiederöffnung, Überblendung/Zoom und PV-Ausschnittdialog. Quellen unverändert; `metadata_only`/Vorschläge sind keine Freigabe. Berichtsfreigaben berücksichtigen Paarrollen.

**Noch offen:** vollständige Orthofotoerzeugung aus Einzelbildern im Verarbeitungsablauf, durchgängige bestätigte KI-Befund-/Modul-/Berichtskette und reale Windows-10-Abnahme. Die zentrale Anlagenübersicht zeigt jetzt gespeicherte Rasterpaare; die Modulbeobachtungstabelle bleibt im eigenen Reiter erhalten. Falschfarben/Rohwerte/Temperaturpunkt ergeben keine bestätigte Celsiusmatrix.

**Freie externe Berechnung:** MicMac-Kern CeCILL-B; V1-Drittkomponenten haben gesonderte Bedingungen. Keine pauschale Binär-/Weiterverteilungsfreigabe, Installation oder bestätigte Kundenverarbeitung. Vorliegende Quellenprüfung in [FREIE_ORTHOFOTO_WERKZEUGE.md](FREIE_ORTHOFOTO_WERKZEUGE.md) weiterverwenden. [GeoTIFF-Ablauf](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md) und [Produktanforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) beachten. Keine neue Engine, kein EPSG erfinden, keine proprietäre Software/SDKs als Ausweichweg.

## Praxisprofil und vertikale Arbeitsweise – Nutzerbestätigung 01.11.2026
Grundlage: Nutzer-PDF **Anforderungen-Solarcheck1.pdf**, Seite 1 (fachlicher Sollablauf), sowie **SolarCheck_Entwicklung_Chronologie_Stand_2026-11-01.pdf** (acht PDF-Seiten, Bestandsnachweis). Nur diese Zusammenfassung übernehmen; Original-PDFs und Kundendateien nicht ins Repository kopieren. Die Chronologie ist kein neuer Implementierungsauftrag und keine Produktabnahme.

**Sollablauf:** Projekt → georeferenzierte RGB-/Thermalfotos importieren → beide Orthofotos mit freier Standardsoftware erzeugen → KI-Befundvorschläge aus Thermal → betroffene PV-Module prüfen/RGB vergleichen → Review → Bericht und Nutzerabnahme → Orthofotos/Bericht exportieren. Offline Windows 10 zuerst; Online erst nach Fertigstellung und Abnahme des Offline-Programms, mit gemeinsamem Python-Fachkern.

**Ist/Soll-Lücken ausdrücklich offen:** Der GeoTIFF-Paarimport ersetzt nicht die Orthofotoerstellung im Verarbeitungsschritt. Überblendung/Zoom sind jetzt auch in der zentralen Anlagenübersicht angebunden. PV-Vorschläge sind keine bestätigte KI-Defektanalyse. Review-/Berichts-/Exportbausteine existieren, ihr durchgängiger Ortho-Befundweg ist nicht abgenommen.

## Fortsetzungspunkt für den nächsten Chat
**Zuletzt abgeschlossen:** **VERT-01A technisch umgesetzt**, ausschließlich synthetisch geprüft. Bestehender Paarimport → zentrale Rasterübersicht → Projektwechsel → SQLite-Wiederöffnung verbunden. Originale unverändert; keine reale Windows-10-, Orthofoto-, PV- oder Temperaturabnahme. Praxisanforderungen und Übergabe bleiben verbindlich.

**Aktiver vertikaler Block VERT-01, teilweise umgesetzt:** Projekt-/Fotoimport → lokale freie Standard-Orthofotoberechnung → zwei gespeicherte GeoTIFFs → zentrale Anlagenübersicht mit Slider und Zoom. VERT-01A abgeschlossen, VERT-01B offen. Keine eigene Rechenengine oder ODM/WebODM/ODX-Anbindung; konkrete freie lokale Toolchain und echte Ergebnisse noch offen.

**VERT-01A abgeschlossen, nicht erneut bauen:** `plant_overview_page.py`/Shell verwenden `project_orthophoto_pairs`, `aligned_preview_arrays` und `OrthophotoComparisonWidget`. Reiter „Orthofotos“ mit Paarauswahl/Überblendung/Zoom, daneben vorhandene Modulbeobachtungen. Projektwechsel und veraltete Qt-Callbacks können kein fremdes Paar anzeigen. Fehlende/defekte/überdeckungslose Raster entfernen die Vorschau und bieten Aktualisierung; Wiederöffnung lädt gespeicherte Paare ohne erneuten Import. Kein Schemawechsel. Tests: `tests/test_gui_plant_orthophotos.py`; in Windows-CI ergänzt. Paarauswahl/Reiter bleiben beim Aktualisieren erhalten; Zoom/Slider sind flüchtiger Anzeigezustand.

**Nächster offener Teil VERT-01B:** Fehlende freie lokale Berechnung aus importierten Einzelbildern an denselben Paar-/Anzeigeweg anbinden. Einstieg: vorhandenes Toolchain-Ergebnis in `FREIE_ORTHOFOTO_WERKZEUGE.md` und Ablauf `EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md` verwenden; konkrete freie lokale Windows-10-Ausführung/Verfügbarkeit vor einem Adapter belegen. Keine pauschale Neurecherche oder ungeprüfte Installation/Ausführung. Echte Bildabnahme nur unter Nutzerkontrolle lokal. **VERT-01A allein schließt VERT-01 nicht ab.**

**Folgeblock VERT-02, noch nicht begonnen:** Ein Thermal-Befundvorschlag → zugehöriges RGB-PV-Modul/stabile ID → Nutzerentscheidung speichern → im Berichtsentwurf wiederfinden → Freigabe/Export. Vorhandene Detektions-, Identitäts-, Review- und Berichtsfunktionen verbinden; Temperaturprovenienz getrennt prüfen. Online/Zahlung/Installer bleiben nachrangig.

**Abschluss eines vertikalen Blocks:** Bedienbarer Nutzerweg mit Eingang und sichtbarem Ergebnis, projektgebunden gespeichert, nach Neustart wiederherstellbar und im nächsten Schritt verwendbar; Fehler-/Abbruchfälle getestet. Technisch geprüft und lokal fachlich abgenommen getrennt ausweisen. CI allein ist keine Produktfreigabe.

## Verbindliche Chat-Übergabe
Beim Start AGENTS, diesen Checkpoint und Anforderungen lesen; lokalen/Remote-HEAD, Änderungen und exakte CI prüfen. Geschlossenen Block und vorhandene Funktionen im Register abgleichen. Am oben genannten offenen Teil fortsetzen. Nur bei nachgewiesener Lücke/Regression einen abgeschlossenen Baustein ändern und den Grund dokumentieren.
Vor Chatende zuerst diesen Checkpoint (1.000–8.500 Zeichen), danach [Register](DEVELOPMENT_STEP_REGISTER.md), [Vereinbarung](DEVELOPMENT_AGREEMENT.md), [Handoff](CHAT_HANDOFF.md) und [Roadmap](PV_ORTHOMOSAIC_FIRST_ROADMAP.md) aktualisieren: Block-ID, Status, Commit/Testbelege, verbleibende Lücke, genauer nächster Einstieg und Abnahmekriterium. Keine pauschalen „fertig“-Aussagen über Teilbausteine.
