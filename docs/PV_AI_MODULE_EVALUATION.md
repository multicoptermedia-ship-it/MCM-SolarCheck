# Lokaler KI-Modellvergleich für PV-Modulgrenzen

Stand17.11.2026 · PV-AI-MODEL-COMPARE-01 · [verbindlicher Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der Nutzer verlangt automatische Verarbeitung großer Anlagen und manuelle Handlung nur bei unklarer Analyse. Der jetzige OpenCV-Farb-/Formdetektor ist eine Heuristik. Dieser Block verbindet die vorhandene Detektorschnittstelle mit einem **lokalen CPU-ONNX-Instanzmodellvergleich**. Der ergänzte PV-Hawk-Pilot lädt inzwischen tatsächlich veröffentlichte trainierte RGB-Gewichte in einer eigenen CPU-Umgebung; noch kein im Feld qualifiziertes Modell, keine Gesamtparkautomatik und keine automatische Qualitätsfreigabe.


**Aktualisierung17.11.:** Zusätzlicher isolierter PV-Hawk-CPU-Pilot vom Nutzer ausdrücklich freigegeben und implementiert. Tatsächliche veröffentlichte RGB-Gewichte/Linux-CPU-Inferenz und gespeicherter Ausschnittvergleich auf synthetischen GeoTIFFs bestanden; eigener expliziter Windows-Einrichtungsstart, keine Installation in SolarCheck/OpenSfM. [Aktueller Start/Prüfstand](PV_HAWK_CPU_PILOT_WINDOWS10.md). Unten beschriebene frühere Freigabenachfrage ist beantwortet; keine erneute Nachfrage. ONNX bleibt optionaler anderer Backendweg; H5 wird direkt in der getrennten TF-Laufzeit geladen. Feldqualität/Produktion/Weitergaberechte weiterhin offen.

## Nutzerplanung28.11.2026: unklare Grenzen gezielt nacharbeiten

**PV-AI-EXCEPTION-REQ-02 ist angefordert, noch nicht als automatische Ausnahmeliste implementiert.** Die bereits vorhandene Oberfläche für Korrigieren/Ergänzen/Löschen/Zoom/Speichern/Wiederöffnung soll später unmittelbar aus einer Liste der Problemstellen erreichbar sein. Gründe und native Position zeigen, RGB/Thermal vergleichen, passende Umrisse/Entscheidungen erhalten. Auch ungeklärte Bereiche ohne erkannten Umriss bleiben sichtbar; keine bestätigten fehlenden Module oder vollständige Erkennung aus der Modellkonfidenz ableiten. Keine1000Pflichtprüfungen und kein automatisches Kundentraining.

**PV-EDGE-CAPTURE-REQ-01:** Nutzer meint einen äußeren Aufnahmepuffer über die Randmodule hinaus, damit Außenkanten/Ecken in mehreren überlappenden Bildern vollständig sichtbar werden. Breite nach Kamera/Bildfeld/Höhe/Blickrichtung und Überlappung bestimmen; keine Vergrößerung der inneren Bahnabstände oder Gleichsetzung mit50%Analysekachel-Überlappung. Empfehlung für künftige Befliegungen, keine neue Flug-/Matching-/Orthofotoaktion am bestehenden Bestand. Details und spätere Abnahme: [REQ-PV-REVIEW-20/REQ-PV-CAPTURE-21](ANFORDERUNGEN_ORTHOFOTO_CODEX.md#req-pv-review-20--gezielte-ausgabe-zur-manuellen-korrektur28112026).

## Tatsächlich implementiert

Gespeicherten RGB-/Thermal-Vergleich → gespeicherten PV-Ausschnitt → mindestens einen Umriss als passend beurteilen/lokal speichern → **KI-Modellvergleich starten(lokal)** → bewusst ausgewählte, bereits auf Auswertungsrechte und Herkunft geprüfte Modellbeschreibung. Der eigene App-Python-Worker lädt nur diese lokalen Gewichte. Keine Internet-/Hub-Anfrage, Installation, Modell-/Datensatzdownload oder Trainingsaktion. OpenCV-DNN auf CPU bleibt die Inferenzlaufzeit; die optionale ONNX-Bibliothek validiert den Graph. `requirements-ai-evaluation.txt` ist eine getrennte optionale Anforderung, nicht Bestandteil des normalen App-Starts. CI/Entwicklung installieren sie für synthetische Vertragstests; beim Nutzer wird nichts automatisch installiert.

Das Modell sieht denselben begrenzten RGB-Ausschnitt(max2048×2048native Pixel). Die vorhandene RGB-Masken-/Polygonprüfung und gespeicherte GeoTIFF-Zuordnung bestimmen Thermalanteile; keine neue Sensorregistrierung. Die vorhandenen bearbeiteten/gelöschten Entwürfe bleiben unverändert. Nur aktive gespeicherte Umrisse mit `outline_ok` bilden die **Teilreferenz**.

Der Vergleich ordnet Kandidaten und Referenzen eindeutig über Polygon-IoU≥0,5 zu. Anzeige: gelbe Referenzen, grüne Kandidaten mit getrennten K-Nummern. Zähler:

- gespeicherte passende Umrisse und davon wiedergefundene;
- nicht wiedergefundene Referenzumrisse;
- zusätzliche, noch ungeprüfte Modellkandidaten.

Eine zusätzliche Erkennung ist **nicht automatisch falsch**, eine nicht gelabelte Fläche kein belegtes Negativbeispiel. Keine Precision/Recall/Vollständigkeit aus dieser Teilreferenz berechnen. Die Bewertung der Feldgenauigkeit braucht unabhängig vollständig gelabelte Testflächen und standortgetrennte Daten. Modellscore ist keine Wahrscheinlichkeit einer korrekten elektrischen Diagnose.

Der Worker läuft separat, maximal5Minuten. **KI-Vergleich abbrechen**, Timeout oder Fensterschließen beendet nur diesen Prozess. Erfolg wird zunächst gestaged, im Elternprozess gegen aktuelle Quellen/gespeicherte Umrisse geprüft und erst dann atomar als `pv-model-comparison.LOCAL.json` übernommen. Fehler/Abbruch erhalten den letzten erfolgreichen Vergleich. **Gespeicherten KI-Vergleich öffnen** lädt ohne Inferenz/Modellimport neu. Geänderte Raster/gespeicherte Modulprüfung entwerten den alten Vergleich. Das lokale JSON enthält private Geometrien/IDs/Modellnachweise und bleibt außerhalb von Git/Cloud/teilbaren Kennzahlen.

Dauerlabel **unvollständig: 280 von 287 Bildern**, GeoTIFF-Tags und reguläre Paarimport-Sperre bleiben erhalten. Quellen/eigene Thermal-Kameralösung/DB unverändert. `production_approved`, `automatically_accepted`, `accuracy_verified`, physische ID-/Abdeckungs-/Geometrie-/Temperaturfreigaben bleiben false. Kein Celsiusnachweis und keine Befunddiagnose durch diese Modulerkennung.

## Modellprofil: bewusst eng und überprüfbar

Profil `opencv-onnx-pv-instance-roi-1`, RGB-Einzelmodul-Instanzsegmentierung mit genau einer Klasse `pv_module`. **Keine** allgemeine COCO-Erkennung, Anlagenflächen-Segmentierung, YOLO-Datei, H5-Datei oder beliebiger ONNX-Export durch bloßes Umbenennen übernehmen.

- Eine feste float32-Eingabe `[1,3,S,S]`, S64–1024; RGB0..1, seitenverhältnistreu mit schwarzem Rand. Exakte Vorverarbeitung muss zum trainierten Modell/Export passen; abweichende Normalisierung muss fachgerecht im Export berücksichtigt werden.
- Drei benannte Ausgaben: `boxes` als `[N,4]` normalisierte xyxy-Koordinaten im Modelleingang, `scores` mit N Werten0..1 und `masks` als `[N,H,W]` mit einzelnen ROI-Masken0..1, H/W2–64. Keine zusammengefasste Anlagenmaske. Max2000Instanzen.
- Vergleichs-Cutoff0,25 und Maskenschwelle0,5 sind Kandidatenfilter, **keine** validierten Freigabeschwellen. Instanzen im Padding/abgeschnittene/mehrdeutige Masken nicht in vollständige Modulrechtecke umdeuten. Bestehende Geometrie-/NoData-Filter anwenden.
- Selbst enthaltenes Standard-ONNX, keine externen Tensordateien, eingebetteten Funktionen, Custom-Domains oder Untergraphen; begrenzte Graph-/Dateigröße. Keine Pickle-/Python-Modellplugins. Vor dem Laden und nach Inferenz Gewichts-SHA256 prüfen, Beschreibung/Runtimeversionen/Herkunft protokollieren.
- Modellbeschreibung≤32KiB, Gewichte≤512MiB, vorhandene lokale absolute Auswahl außerhalb Git ohne Symlink-Vorfahren. Gewichte direkt neben der Beschreibung. Vergleichsbericht≤16MiB.

Beispielschema für den **noch nicht freigegebenen** Kandidaten, kein ausgeliefertes Modell und keine erfundene Genehmigung:

```json
{
  "profile": "opencv-onnx-pv-instance-roi-1",
  "task": "pv_module_instance_segmentation",
  "classes": ["pv_module"],
  "weights": "reviewed-pv-model.onnx",
  "input_size": 512,
  "evaluation_allowed": false,
  "production_approved": false,
  "code_license": "UNREVIEWED",
  "reviewer": "noch zu prüfen",
  "rights_evidence": "Code-, Gewichts- und erforderliche Datenrechte getrennt belegen",
  "model": {
    "provider": "noch zu qualifizieren",
    "model_version": "noch zu qualifizieren",
    "modality": "rgb",
    "dataset": "Herkunft noch zu belegen",
    "license_id": "UNREVIEWED",
    "weights_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "preprocessing": "rgb-unit-letterbox",
    "backend": "opencv-dnn-cpu"
  }
}
```

Erst nach tatsächlicher Rechteprüfung und erfolgreicher Format-/Vorverarbeitungsprüfung dürfen echte Identität, Gewichtsprüfsumme, Lizenz und Nachweise eingetragen werden. Die lokale Erklärung ist **keine kryptografische Attestation oder anwaltliche Freigabe**. Das Profil akzeptiert für die reine Auswertung explizit geprüfte MIT/Apache-2.0/BSD-3-Clause-Codeangaben und MIT/Apache-2.0/BSD-3-Clause/CC-BY-4.0-Gewichtsangaben. Dies ändert keine bestehenden Produktions-/Verteilungs-/Trainingsgates und genehmigt keine kommerzielle Modellverteilung.

## Primärquellenprüfung: Modell noch offen

Am17.11.2026 nur öffentliche Dokumentation/Code-/Release-Metadaten gelesen. Keine öffentlichen Trainingsbilder/Modellgewichte heruntergeladen und keine Kundenbilder geöffnet.

| Kandidat | Nachweis | Offener Punkt / Entscheidung |
| --- | --- | --- |
| PV-Hawk, Mask R-CNN für einzelne PV-Module in RGB/IR | [Dokumentation](https://lukasbommes.github.io/PV-Hawk/finetune_segmentation.html), [Installation](https://lukasbommes.github.io/PV-Hawk/installation.html), [MIT-Code](https://github.com/LukasBommes/PV-Hawk/blob/master/LICENSE), [Releasev1.0.0](https://github.com/LukasBommes/PV-Hawk/releases/tag/v1.0.0) | RGB-Datei `mask_rcnn_pv_modules_rgb_0059.h5`,255858144Bytes laut Release-API. Dokumentierter Ubuntu/Docker-/älterer TensorFlow-Laufweg, kein passender ONNX-Export. Separate Gewichtsrechte in den gelesenen Hinweisen nicht eindeutig belegt; weder Gewichts-SHA noch Windows10-CPU-Kompatibilität geprüft. Fachliche Referenz, **noch kein aktivierter Kandidat**. |
| CVUT PVsegmentation | [Originalquelle](https://imr.ciirc.cvut.cz/Datasets/PVsegmentation), öffentliche Beschreibung: >3000Modulmasken, RGB/Thermal und U-Net-/YOLOv8-Modelle | Direkter Abruf503/Timeout; Artefakt-/Lizenz-/Formatprüfung nicht abgeschlossen. Nicht herunterladen/aktivieren ohne diese Prüfung. |
| Multi-Resolution PV-System Segmentation | [Originalprojekt](https://github.com/Kleebaue/multi-resolution-pv-system-segmentation) | Öffentliches ONNX-Angebot für **PV-Systemflächen**, kein Nachweis einzelner Module. Daher kein Ersatz für1000Einzelmodul-Instanzen; Rechte separat offen. |
| Ultralytics-basierte PV-Exporte | Projekt-/Modellkarten benennen teils AGPL-3.0 | Keine automatische Übernahme unter bestehender gebührenfreier/proprietärer Modellpolitik. Bestehende Lizenzgates bleiben. |
| RT-DETR | [Apache-2.0-Projekt](https://github.com/lyuwenyu/RT-DETR) bereits als Kandidat dokumentiert | Frameworklizenz allein liefert keine PV-trainierten Einzelmodulmasken und keine Gewichts-/Datensatzfreigabe. |

**Nächster notwendiger Schritt:** Ein konkretes rechtlich und technisch geeignetes PV-Instanzmodell/Export bestimmen, Gewichte und Vorverarbeitung qualifizieren und erst dann im Vergleich auf wenigen bewusst lokal gewählten geprüften Ausschnitten testen. Ein eventueller getrennter TensorFlow-/Exportversuch für PV-Hawk wäre ein **separater bewusst einzurichtender** Versuch; keine automatische Installation/Übernahme seiner Video-/SfM-/Docker-Pipeline. Bestehende Orthofotos und Windows10 bleiben Grundlage. Danach Gesamtflächen-/Ausnahmenverarbeitung mit unabhängig bestimmten Fehler-/Unsicherheitsschwellen, erst anschließend Thermal-Befundanalyse.

## Testbelege und Grenzen

134gezielte synthetische Tests grün. Neue Fälle führen **tatsächliche OpenCV-CPU-Neuralinferenz mit einem synthetischen NN-Vertragsgraph** aus, prüfen RGB/Letterbox, Format/Hashes/Rechte/externe Tensoren, CLI und Qt→Worker→Vergleich→Speichern→Wiederöffnung, Fehler/Abbruch/Timeout/Schließen und unveränderte Quellen/Entwürfe/Paarimport-Sperre. Der Graph hat künstlich gesetzte Testgewichte und ist ausdrücklich **kein trainiertes PV-Erkennungsmodell**. Neue CI am exakten HEAD prüfen; synthetische Erfolge belegen keine reale Feldleistung oder1000-Modul-Tauglichkeit.

## Historischer Vorschlag für den inzwischen bestätigten PV-Hawk-Versuch

Für das ausgewählte RGB-Artefakt ist ein separater technischer CPU-Versuch sinnvoll, bevor Gewichtsrechte, korrekte Vorverarbeitung, Export und Feldqualität als abgeschlossen gelten können. Das ist eine zusätzliche Laufzeit gegenüber der bisherigen SolarCheck-/OpenSfM-Einrichtung und noch **nicht** eingerichtet/gestartet.

- Privater neuer Ordner `E:\SolarCheck-PV-KI-Pilot\`; eigenes Environment. Das vorhandene F:-SolarCheck-Python, die produktive SQLite und das vorhandene OpenSfM-Environment bleiben erhalten. Vorhandenes Python3.10 kann als Basis dienen; kein neuer Compiler-/CUDA-/SDK-Auftrag.
- Konkreter Referenzstand: PV-Hawk `v1.0.0`, nur dessen Modulsegmentierung/MIT-Code; RGB-Datei `mask_rcnn_pv_modules_rgb_0059.h5`,255858144Bytes aus dem Originalrelease. Keine Video-/SfM-/Docker-Pipeline übernehmen.
- CPU-Paketkandidaten: TensorFlow-CPU2.10.1/Keras2.10.0, NumPy1.23.5, h5py3.7.0, SciPy1.9.3, scikit-image0.19.3. Am17.11.2026 wurden anhand der **PyPI-Metadaten** passende cp310-win_amd64- bzw. plattformunabhängige Wheels geprüft. **Das belegt noch keine funktionierende PV-Hawk-/Windows10-Kombination.** Weitere Abhängigkeiten/Third-Party-Texte und Änderungen für dessen ältere Keras-API vor Ausführung gesondert prüfen. Keine automatische Installation.
- Zuerst reproduzierbares Laden und synthetische CPU-Inferenz, anschließend Rechte-/Export-/Vorverarbeitungsprüfung. Erst danach bewusster begrenzter lokaler Vergleich mit vorhandenen geprüften PV-Ausschnitten; Kundendaten nicht nach Codex/Git/Cloud. Echte Erkennungsqualität und Prüfaufwand messen, keine Gesamtparkfreigabe vorziehen.

Paketprimärquellen: [TensorFlow-CPU2.10.1](https://pypi.org/project/tensorflow-cpu/2.10.1/), [Keras2.10.0](https://pypi.org/project/keras/2.10.0/), [NumPy1.23.5](https://pypi.org/project/numpy/1.23.5/), [h5py3.7.0](https://pypi.org/project/h5py/3.7.0/), [SciPy1.9.3](https://pypi.org/project/scipy/1.9.3/), [scikit-image0.19.3](https://pypi.org/project/scikit-image/0.19.3/).

Eine Bestätigung für diesen zusätzlichen isolierten Laufzeit-/Modellversuch ist **keine** rechtliche Produktions-/Verteilungsfreigabe und keine Zustimmung zum Hochladen oder Training mit Kundendaten. Hintergrund der separaten Nachfrage: [REQ-ORTHO-03 in ANFORDERUNGEN_ORTHOFOTO_CODEX.md](ANFORDERUNGEN_ORTHOFOTO_CODEX.md#anforderungen) verlangt „Keine automatische Installation oder Fremdsoftware-Ausführung ohne Freigabe.“ Der bisher ausdrücklich freigegebene und abgeschlossene OpenSfM-Setupblock enthält diese zusätzliche TensorFlow-Testumgebung nicht.
