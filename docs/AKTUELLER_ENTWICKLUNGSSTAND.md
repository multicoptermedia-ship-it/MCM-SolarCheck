# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md) und [Produktanforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) lesen. Nutzerentscheidung vom 31.10.2026: zwei extern berechnete Orthofotos, RGB und Thermal.** Neueste Nutzeranweisung hat Vorrang vor älteren Planungen.

## Auftrag und Repository
Benötigt werden **ein RGB-Orthofoto und ein Thermal-Orthofoto**, zweidimensional und georeferenziert. Etablierte kostenfreie Open-Source-Software übernimmt die Berechnung; **keine neue Photogrammetrie-Engine**, kein eigener SfM-/BA-/Stitch-/Dachalgorithmus.
Aktiv: **`multicoptermedia-ship-it/MCM-SolarCheck`**, Branch `feature/orthofoto-license-neutral-rgb-first-20261028`, Draft **PR #9**. Die frühere Nur-Lese-Sperre ist aufgehoben. SolarCheck 2 unverändert lassen. **Kein Merge/Push nach `main`.**
Windows 10/offline zuerst. Keine proprietäre/kostenpflichtige Software und keine ODM/WebODM/ODX-Anbindung, Ausführung oder Paketierung durch SolarCheck. Eigenes WebODM bleibt ausschließlich manuell außerhalb der App zulässig. Kundenbilder/GPS/RTK/SQLite/echte Raster nie in GitHub, CI oder Cloud übertragen; nur Quellcode und synthetische Tests lesen. Keine private Rohbildinventur oder autonome Bildöffnung.

## Gesicherte Basis
Letzter abgeschlossener Codeblock: **DEV-EXTERNAL-ORTHOPHOTO-PAIR-001**, Code-HEAD `a9a5b6c144d0f70c29fdbcae8bd1e317c01dc9b1`. Lokale Suite: 4.113 bestanden, 15 Skips. Sechs CI-Jobs unter Python 3.11/3.12 erfolgreich: [Linux Push](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/41295557040), [Linux PR](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/41295561826), [Windows PR](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/41295561666). Für spätere HEADs eigene CI lesen.
Historische Kennung **DEV-RGB-ORTHO-ENGINE-001**: **3D-Entwicklung bis auf Weiteres einfrieren**. Eigene SfM-/BA-/Stitch-/Dachforschung ist eingefroren und kein Lieferpfad. Der frühere reale Windows-10-Gesamtmosaiktest bleibt FAIL. Kein erneuter Forschungs-/Inventurstart.

## Vorhandene Funktionen und Grenzen
**DEV-EXTERNAL-ORTHOPHOTO-PAIR-001 ist technisch umgesetzt:** vorhandene GeoTIFF-Prüfung/Registrierung um atomare RGB-/Thermal-Paare in SQLite-Schema 22 erweitert; Rollen/Herkunft, Masken/Alpha/NaN-NoData und unterschiedliche CRS/Auflösungen geprüft. Der vorhandene PV-Detektor arbeitet auf gewählten RGB-Fenstern und ordnet Polygone über CRS/Affine mit korrekten Pixelzentren dem Thermalraster zu. Importseite bietet Paarregistrierung, Wiederöffnung, Überblendung/Zoom und PV-Ausschnittdialog. Quellen unverändert; `metadata_only`/Vorschläge sind keine Freigabe. Berichtsfreigaben berücksichtigen Paarrollen.

**Noch offen:** vollständige Orthofotoerzeugung aus Einzelbildern im Verarbeitungsablauf, zentrale rasterbasierte Anlagenübersicht, durchgängige bestätigte KI-Befund-/Modul-/Berichtskette und reale Windows-10-Abnahme. Derzeit ist die Anlagenübersicht eine Modulbeobachtungstabelle; der Rasterviewer liegt im Importbereich. Falschfarben/Rohwerte/Temperaturpunkt ergeben keine bestätigte Celsiusmatrix.

**Freie externe Berechnung:** MicMac-Kern CeCILL-B; V1-Drittkomponenten haben gesonderte Bedingungen. Keine pauschale Binär-/Weiterverteilungsfreigabe, Installation oder bestätigte Kundenverarbeitung. Vorliegende Quellenprüfung in [FREIE_ORTHOFOTO_WERKZEUGE.md](FREIE_ORTHOFOTO_WERKZEUGE.md) weiterverwenden. [GeoTIFF-Ablauf](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md) und [Produktanforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) beachten. Keine neue Engine, kein EPSG erfinden, keine proprietäre Software/SDKs als Ausweichweg.

## Praxisprofil und vertikale Arbeitsweise – Nutzerbestätigung 01.11.2026
Grundlage: Nutzer-PDF **Anforderungen-Solarcheck1.pdf**, Seite 1 (fachlicher Sollablauf), sowie **SolarCheck_Entwicklung_Chronologie_Stand_2026-11-01.pdf** (acht PDF-Seiten, Bestandsnachweis). Nur diese Zusammenfassung übernehmen; Original-PDFs und Kundendateien nicht ins Repository kopieren. Die Chronologie ist kein neuer Implementierungsauftrag und keine Produktabnahme.

**Sollablauf:** Projekt → georeferenzierte RGB-/Thermalfotos importieren → beide Orthofotos mit freier Standardsoftware erzeugen → KI-Befundvorschläge aus Thermal → betroffene PV-Module prüfen/RGB vergleichen → Review → Bericht und Nutzerabnahme → Orthofotos/Bericht exportieren. Offline Windows 10 zuerst; Online erst nach Fertigstellung und Abnahme des Offline-Programms, mit gemeinsamem Python-Fachkern.

**Ist/Soll-Lücken ausdrücklich offen:** Der GeoTIFF-Paarimport ersetzt nicht die Orthofotoerstellung im Verarbeitungsschritt. Überblendung/Zoom existieren im Importbereich; die Anlagenübersicht ist noch eine Tabelle von Modulbeobachtungen. PV-Vorschläge sind keine bestätigte KI-Defektanalyse. Review-/Berichts-/Exportbausteine existieren, ihr durchgängiger Ortho-Befundweg ist nicht abgenommen.

## Fortsetzungspunkt für den nächsten Chat
**Zuletzt abgeschlossen:** Praxis-PDFs gelesen, mit Code abgeglichen und Anforderungen/Übergabe synchronisiert. In diesem Dokumentationsblock keine neue Programmfunktion und kein neuer Reallauf.

**Aktiver nächster vertikaler Block VERT-01:** Projekt-/Fotoimport → lokale freie Standard-Orthofotoberechnung → zwei gespeicherte GeoTIFFs → zentrale Anlagenübersicht mit Slider und Zoom. Keine eigene Rechenengine, keine ODM/WebODM/ODX-Anbindung. Die vorliegende MicMac-Lizenzprüfung wiederverwenden; konkrete lokale Toolchain/Installation und echte Ergebnisse sind noch offen.

**Erster konkreter Teil VERT-01A, noch nicht begonnen:** Bereits gespeichertes RGB-/Thermal-Paar des aktiven Projekts in der **Anlagenübersicht** anzeigen. Bestehende `project_orthophoto_pairs`, `aligned_preview_arrays` und `OrthophotoComparisonWidget` weiterverwenden; `plant_overview_page.py`/Shell verbinden. Projektwechsel, Wiederöffnung, Masken, Slider und Zoom in derselben Bedienkette prüfen. Vorher Code/aktuellen HEAD lesen; nicht Paarimport oder Viewer erneut bauen.

**Danach VERT-01B:** Fehlende freie lokale Berechnung aus importierten Einzelbildern an denselben Paar-/Anzeigeweg anbinden. Toolrechte/Verfügbarkeit vor Ausführung klären, vorhandene Recherche nicht wiederholen. Echte Bildabnahme nur unter Nutzerkontrolle lokal. **VERT-01A allein schließt VERT-01 nicht ab.**

**Folgeblock VERT-02, noch nicht begonnen:** Ein Thermal-Befundvorschlag → zugehöriges RGB-PV-Modul/stabile ID → Nutzerentscheidung speichern → im Berichtsentwurf wiederfinden → Freigabe/Export. Vorhandene Detektions-, Identitäts-, Review- und Berichtsfunktionen verbinden; Temperaturprovenienz getrennt prüfen. Online/Zahlung/Installer bleiben nachrangig.

**Abschluss eines vertikalen Blocks:** Bedienbarer Nutzerweg mit Eingang und sichtbarem Ergebnis, projektgebunden gespeichert, nach Neustart wiederherstellbar und im nächsten Schritt verwendbar; Fehler-/Abbruchfälle getestet. Technisch geprüft und lokal fachlich abgenommen getrennt ausweisen. CI allein ist keine Produktfreigabe.

## Verbindliche Chat-Übergabe
Beim Start AGENTS, diesen Checkpoint und Anforderungen lesen; lokalen/Remote-HEAD, Änderungen und exakte CI prüfen. Geschlossenen Block und vorhandene Funktionen im Register abgleichen. Am oben genannten offenen Teil fortsetzen. Nur bei nachgewiesener Lücke/Regression einen abgeschlossenen Baustein ändern und den Grund dokumentieren.
Vor Chatende zuerst diesen Checkpoint (1.000–8.500 Zeichen), danach [Register](DEVELOPMENT_STEP_REGISTER.md), [Vereinbarung](DEVELOPMENT_AGREEMENT.md), [Handoff](CHAT_HANDOFF.md) und [Roadmap](PV_ORTHOMOSAIC_FIRST_ROADMAP.md) aktualisieren: Block-ID, Status, Commit/Testbelege, verbleibende Lücke, genauer nächster Einstieg und Abnahmekriterium. Keine pauschalen „fertig“-Aussagen über Teilbausteine.
