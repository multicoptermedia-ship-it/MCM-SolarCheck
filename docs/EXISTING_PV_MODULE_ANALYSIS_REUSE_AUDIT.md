# Vorhandene PV-Modulerkennung und Analyse wiederverwenden – Bestandsaufnahme

Stand: 2026-10-24. Grundlage: bestehender Entwicklungszweig
`feature/offline-human-report-approval` und bestehende historische Dokumentation
(siehe unten). **Keine neue Algorithmenimplementierung** durch dieses Dokument.
Keine DJI-Originalbilder, GPS-Positionen, Kundendaten, Einzelbildbefunde oder
lokalen Dateipfade werden nach GitHub übertragen.

## Klares Ergebnis

**Die Erkennungs-, Auswertungs-, Verknüpfungs- und Validierungsbausteine sind
bereits in beträchtlichem Umfang vorhanden.** Neue Aufgaben sollen zuerst
die vorhandenen Funktionen wiederverwenden und integrieren; eine neue parallele
PV-Modulerkennung wäre unnötige Doppelarbeit.

Nicht gleichsetzen: getesteter Algorithmus/Vertrag, heuristisch gestützter
Modulvorschlag, fachlich bestätigtes PV-Modul, geometrisch registriertes
RGB/Thermal-Paar und vollständig nachgewiesene Projektverarbeitung.

## Wiederverwendungslandkarte

| Bestehender Code | Wiederverwendbarer Zweck | Grenze |
|---|---|---|
| `vision/grid_module_backend.py`, `grid_module_detector.py`, `grid_cell_support.py` | Rasterlinien, endliche strukturelle Stützung und Zellpolygone | Wiederholte Linien/Teilzellen können mehrdeutig sein |
| `vision/opencv_module_detector.py` | Unabhängige bildbasierte Heuristik auf RGB-Pixeln, auch `detect_array()` | Keine abgesicherte Erkennungsgenauigkeit für alle Dachtypen |
| `vision/confirmed_module_detector.py`, `module_fusion.py` | Nur räumlich übereinstimmende Struktur-/Bildvorschläge akzeptieren | `confirmed` bedeutet **algorithmisch gestützt**, nie Expertenentscheidung |
| `vision/cadence_module_detector.py`, `cadence_gate.py`, `cadence_phase_selection.py` | Umgang mit periodischen Gitterabständen, separaten Plausibilitäts-Gates | Auf realem Bildmaterial gezielt nachvalidieren |
| `vision/module_detection_pipeline.py`, `module_batch.py`, `module_quality.py` | Frameweise/batchweise Detektoren ausführen, normalisieren, geometrisch prüfen | Noch kein vollständiger Offline-GUI-Worker über den gesamten realen Bestand |
| `vision/module_diagnostics.py`, `module_evaluation.py`, `module_real_evaluation.py`, `module_acceptance.py` | Vergleich, Zähler, Entwickler-Abnahmekriterien und Diagnose | Ausführungskonsistenz ist **nicht** Precision/Recall gegen unabhängige Labels |
| `vision/module_identity.py`, `module_identity_pipeline.py`, `module_consistency.py` | Modulbeobachtungen und physische Identität mit gemeinsamem Koordinatensystem | Frameübergreifende Identität ohne validierte Registrierung gesperrt |
| `vision/cross_sensor_assignment.py`, `finding_linkage.py`, `pairing/geometry.py` | Thermische Befunde über *validierten* PixelTransform einem einzelnen RGB-Modul zuweisen | Metadaten-Bildpaarung allein genügt nicht |
| `thermal/m3t_radiometric.py`, `thermal/analysis.py`, `thermal/quality.py` | Echte 16-Bit-Rohwerte, Statistik und nichtkalibrierte Kandidaten | Keine physikalische °C-Kalibrierung |
| `thermal/temperature_provider.py`, `thermal/temperature_provenance.py` | Konservativer Temperatur-Provider-Vertrag, Celsius-Provenienz-Gate | Referenzbackend für DJI-Celsius weiterhin explizit nicht validiert |
| `services/module_camera_calibration_gate.py`, `module_plane_projection.py`, `module_plane_rectification.py`, `module_surface_pipeline.py` | Geprüfte Kamerageometrie, Modulfläche, perspektivische Entzerrung und Mosaik | Echte Kalibrier-, Vermessungs- und Kontrollnachweise separat erforderlich |
| `review/classification.py`, `services/offline_torchvision_classifier.py` | Beratende Klassen- und Modellvertrags-Bausteine | Optionaler lokaler Trainer ist experimentell; keine automatisch bestätigten Defekte |
| `storage/sqlite.py` | Vorhandene `pv_modules`- und `module_identity_links`-Persistenz mit atomaren Schreibmethoden | Niemals rohe/ungeprüfte Vorschläge blind in Persistenz übernehmen |

Das **existierende** lokale, rein lesende 1–3-RGB-Verfahren in
`services/offline_module_sample.py` verwendet schon
`GridModuleDetector`, `OpenCVModuleDetector`,
`fuse_module_detections` und `filter_module_detections`.
Es ist deshalb **kein neuer Detektor erforderlich**, um erste diagnostische
Vergleiche zu machen.

## Historische Realbild-Baselines – bereits 2026-09

- `docs/pv-module-real-data-evaluation.md` hält acht reale
  M3T-Entwicklungsframes, Bild-/Gittervorschlagszahlen, Überlappungen und
  die damalige finite-segment-support-Anforderung fest. Die dortigen Zähler
  stammen aus einem **früheren Algorithmusstand**, sind keine aktuelle
  Accuracy-Messung.
- `docs/validation/m3t-global-grid-real-data-2026-09-17.md`
  und `docs/validation/m3t_global_grid_real_pairs_2026-09-18.md`
  dokumentieren frühere reale RGB/Thermal-Registrierungsversuche.
  Wiederholte Gitterabstände, unterschiedliche Rasterauflösung und
  Achsenmehrdeutigkeit waren blockierende Ursachen; Fail-Closed-Verhalten
  ist beabsichtigt. Diese Datensätze sind nicht identisch mit jedem
  später importierten Pilotprojekt.
- `docs/validation/phase8-production-model-closure.md` bestätigt
  abgeschlossene **Softwareverträge**, aber ausdrücklich **keine**
  wissenschaftlich validierten und rechtlich freigegebenen
  Produktionsmodellgewichte.
- `docs/validation/phase10-application-integration-plan.md`
  beschreibt die wesentliche verbleibende Aufgabe: bestehende
  getrennte Domain-/Analysebausteine **zu einem sicher nachgewiesenen
  Anwendungsablauf verbinden**.

## Nächster Entwicklungsweg: integrieren statt neu erfinden

1. **Bestehendes Moduldiagnostik-Sample fachlich auswertbar machen:**
   Vorhandene `GridModuleDetector.detect_with_diagnostics_array()`,
   `OpenCVModuleDetector.detect_array()`, `module_diagnostics` und
   `module_evaluation` wiederverwenden. Diagnose je Bild liefert klar
   getrennt Linien-/Kandidatenzahlen, Ausschlussgrund und räumliche
   Überlappung. Nur redigierte/Zähler-Ausgaben ohne Originalbytes;
   bei visueller Prüfung private Bildvorschau strikt lokal und read-only.
2. **Gates anhand echter, ausdrücklich für Entwicklung freigegebener
   Beispiele prüfen:** Die alten September-Baselines als Regression
   wiederverwenden; die 0-Überlappungsfälle analysieren, keine IoU- oder
   Homografie-Toleranzen locker einstellen, um scheinbaren Erfolg zu
   erzeugen. Ein separates, unabhängig manuell gelabeltes Holdout
   für die spätere Accuracy-Abnahme bewahren.
3. **Projektweiter Worker nur nach vorbereiteter Validierung:** Vorhandene
   `module_batch`-, Identitäts-, Geometrie-, Speicher- und Workflow-Verträge
   einbinden, mit Abbruch, Fortschritt, Eingabefingerabdruck, einzelnen
   überprüfbaren Phasenbelegen und unveränderlichen Originaldateien.
4. **Gesamtfreigabe weiterhin gesperrt:** Solange kein nachweislich
   vollständiger Modul-/Befund-/Registrierungs-/Kalibrierungs-Workflow
   existiert, darf ein technischer Teiltest niemals Review, Bericht
   oder Export freigeben. Die bereits implementierte
   `services/offline_review_gate.py`-Sperre beibehalten.

## Explizite Stoppliste

- Keine neue PV-Moduldetektor-Implementierung, bevor vorhandene Varianten
  und reale September-Gates überprüft wurden.
- Keine Behauptung, ein Gitterzellenvorschlag oder ein algorithmisch
  `confirmed` Polygon sei vom Menschen bestätigtes PV-Modul.
- Keine erfundenen Celsiuswerte, absolute Hotspot-GPS-Punkte oder
  Bildregistrierung allein aus Aufnahmecounter-Zuordnung.
- Keine automatischen Review-/Report-/Export-Freigaben, auch nicht nach
  synthetisch bestandenen Tests.
- Keine produktiven oder privaten DJI-Quelldaten in GitHub, CI oder
  unkontrollierte Trainingspfade.

Zweck dieser Bestandsaufnahme: bereits entwickelte Arbeit aktiv
wiederverwenden, statt sie in neuen, voneinander getrennten Stufen erneut
aufzubauen.
