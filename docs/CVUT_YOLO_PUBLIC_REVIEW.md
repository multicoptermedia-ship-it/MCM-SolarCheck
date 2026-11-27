# CVUT-YOLO: öffentlicher Erkennungsbefund vom 27.11.2026

Das bereitgestellte Paket enthält vortrainierte RGB-Modellgewichte. Der Zugriff ist gelöst. Die öffentliche Prüfung belegt einen Fortschritt bei den PV-Flächen, aber noch keine brauchbare automatische Modulzählung. Dafür ist **kein neuer Installations- oder unveränderter Wiederholungslauf beim Nutzer** erforderlich.

## Eingang und kontrolliertes Laden

Die Datei heißt tatsächlich `PV_module_segmentation_dataset.zip` und ist 699176611 Bytes groß. Aus dem ZIP wurden nur Verzeichnis, zwei RGB-Gewichtsdateien und die jeweiligen Trainingsparameter gelesen. Die 820 enthaltenen Bilddateien wurden nicht gelesen oder dekodiert. Der persönliche Übertragungslink gehört nicht ins Repository.

| Ausgewähltes RGB-Mitglied | Größe | Beobachtete SHA256 |
| --- | ---: | --- |
| `RGB/yolo_training/modules2_trained_YOLOv8n/weights/best.pt` | 6806691 | `e464ffde55d91727b19c8690706d79b70a3deb2398d7d564bb7a0a2656fea6e6` |
| `RGB/yolo_training/modules2_trained_YOLOv8s/weights/best.pt` | 23896931 | `549c6d78ba9e44cfd3936062fa74510468ae57bdb91c5fa9116a5662d999674f` |

CRC und lokal beobachtete Mitglied-SHA stimmen. Dies ist keine Anbieterattestation und keine Prüfung der vollständigen ZIP-SHA. Die Metadaten nennen Ultralytics 8.1.29, Segmentierung, Klasse `module`, 640 Pixel, 200 Trainingsepochen und AGPL-3.0.

Fremde serialisierte Klassen werden beim eingeschränkten `weights_only=True`-Laden zu passiven Datencontainern. Ein erforderlicher `getattr`-Verweis ist auf einen unbenutzbaren bekannten Methodennamen begrenzt. Keine geladene Modellmethode, kein Hook und kein `state_dict()` auf dem Fremdobjekt werden ausgeführt. Nur geprüfte CPU-Tensorwörterbücher gelangen in eine frisch aufgebaute Standardarchitektur. Kein unsicherer Ladefallback.

Die eigene Cloud-Testumgebung nutzt Torch 2.15.0 CPU, torchvision 0.29.2 CPU und Ultralytics 8.1.29. Bestehende App-/Torch-/PV-Hawk-Umgebungen und Nutzerinstallationen wurden erhalten. [Eigene Forschungsabhängigkeiten](../requirements-cvut-yolo-research-cpu.txt) gehören nicht zum App-Setup. Neue CI-Referenztests arbeiten ausschließlich mit erzeugten Bildern und Gewichten.

## Gemessener Befund

Alle folgenden Ergebnisse betreffen **dieselben 24 öffentlichen Validierungsausschnitte der Anlage 033 mit 117 Modulbeobachtungen**. Überlappende Ansichten sind keine 117 unabhängig bestätigten physischen Module. Masken-IoU mindestens 0,5 und eindeutige maximale Trefferzuordnung; unbekannte Pixel werden bei der Bewertung ignoriert. Die Referenzmaske und die Referenzanzahl gehen niemals in die Erkennung ein.

| Versuch | Passende Masken | Zusätzliche Vorschläge | Fehlende Referenzen |
| --- | ---: | ---: | ---: |
| Veröffentlichtes n, Eingabe 640 | 28 | 441 | 89 |
| Veröffentlichtes n, Eingabe 320 | 41 | 377 | 76 |
| Veröffentlichtes s, Eingabe 640 | 34 | 297 | 83 |
| n, Kopf angepasst, 20 Epochen | 49 | 89 | 68 |
| n, zusätzliche 009-Kontexte, weitere Modellteile | 68 | 132 | 49 |
| n, zusätzliche 009-Kontexte, alle trainierbaren Faltungen | 84 | 185 | 33 |
| n, drei Trainingsanlagen, ausgewählte Epoche 8 | 90 | 129 | 27 |
| Derselbe letzte Kandidat, vollständige gefilterte Modul-Umrisse | **59** | **45** | **58** |

Die Eingabegrößen der veröffentlichten Modelle sind ausdrücklich verschiedene Forschungsprofile. Die letzten Anpassungen verwenden den vorhandenen Vertrag: nativer 512er-Ausschnitt, exakte 2×2-RGB-Mittelung auf 256, konservative Gültigkeitsmaske. Die bessere Rohflächen-IoU von 0,89024 bestätigt keine richtige Modultrennung. Auch die endgültige Anzahl 104 statt 117 ist keine nur um 13 Module falsche Erkennung: Es fehlen 58 Referenzen, während 45 andere Umrisse zusätzlich entstehen.

Zunächst wurde nur der Kopf, dann weitere und schließlich alle trainierbaren Faltungen angepasst; BatchNorm-Statistiken und -Parameter sowie die DFL-Projektion bleiben eingefroren. Der zusätzliche Verlustadapter berücksichtigt ausschließlich bekannte Anker und bekannte Maskenpixel im Objektkasten. Direkte Gradienten an unbekannten Klassifikations-, Koeffizienten- und Prototypausgaben sind exakt null. Der Bildkontext eines Faltungsnetzes kann trotzdem von Nachbarpixeln abhängen; eine Nullgradient-Garantie für unbekannte Eingabepixel wird nicht behauptet.

Der letzte begrenzte Versuch verwendet je 20 Bilder aus den öffentlichen Trainingsanlagen 009/018/029 mit 80/75/77 räumlich getrennten Ausschnitten und 250/291/293 Modulbeobachtungen. Die beiden Zusatzarchive wurden vollständig im RAM gegen die Anbieter-SHA geprüft; gespeichert wurden nur ausgewählte numerische RGB-/Instanzdaten. Zehn Epochen, 2320 AdamW-Updates, Lernrate 0,00003, Clip 10, Seed 6400; Auswahl nach Rohmasken-F1 auf 033. Kandidat-SHA: `d80be7a0629da05e4f315e3a8ead0fb2438649c191a123a33e14403a334cdc27`.

Es gab mehrere Entscheidungen anhand derselben Validierungsanlage. Die Tabelle ist ein Entwicklungsbefund, keine unabhängige Genauigkeitsmessung. Testanlage 024 blieb ungelesen. Morphologisches Zusammenführen wurde verworfen, weil es benachbarte Module verschmilzt. Mehrere Maskenteile derselben vorhergesagten Instanz werden gemeinsam betrachtet; Fragmente unterschiedlicher Instanzen werden nicht einfach zusammengefügt. Rand-, Füllungs-, Seitenverhältnis-, Geometrie- und Dublettenprüfung bleiben ausdrücklich Teil des letzten Ergebnisses.

## Gespeicherter Prüfweg

[Prüfskript](../scripts/MCM_SolarCheck_CVUT_YOLO_PRUEFUNG.py), [Gewichts-/Verlusthelfer](../src/mcm_solarcheck/vision/cvut_yolo_research.py) und [Modulbewertung](../src/mcm_solarcheck/vision/cvut_yolo_validation.py) bilden einen getrennten Entwicklerweg. Sie installieren und trainieren nichts. Der Aufruf benötigt den bereits geprüften öffentlichen Korpus und die ursprüngliche n-Gewichtsdatei; ein abweichender experimenteller Tensorkandidat braucht zusätzlich seine ausdrücklich angegebene SHA256. Er erzeugt einen neuen JSON-Bericht und überschreibt keinen vorhandenen Bericht. Abbruch veröffentlicht keinen fertigen Teilbericht.

Der bereits gespeicherte Befund lässt sich aus dem Repository-Hauptordner ohne Torch und ohne Modellaufruf öffnen:

```powershell
python .\scripts\MCM_SolarCheck_CVUT_YOLO_PRUEFUNG.py --show .\docs\evidence\cvut-yolo-module-validation-2026-11-27.json
```

Dies ist eine Textausgabe, kein neuer GUI- oder Trainingsstart. Es ist kein notwendiger nächster Nutzerlauf.

[Gesamtbelege](evidence/cvut-yolo-public-2026-11-27.json) enthalten Zahlen, Hashes, Anpassungshistorien und die technische ONNX-Gegenprobe. [Historische Versuchsquellen](evidence/cvut-yolo-public-2026-11-27-sources.zip) enthalten ausschließlich Quelltexte, keine Bilder/Gewichte oder privaten Links. Die dortigen Einmalskripte dokumentieren die Cloud-Prototypen mit festen temporären Pfaden; sie sind kein produktiver Windows-Trainer. Manche Intake-Helfer wurden nach der Probe verschärft; Erfassungs-SHA ersetzt keinen behaupteten identischen Importzeitpunkt. Das experimentelle Training unterstützt keinen hier behaupteten Optimizer-Resume.

Eine frühere ONNX-Ausgabe wurde mit echten OpenCV-CPU-Aufrufen und Torch verglichen. Sie gehört zum **vorherigen** Kandidaten `0c42dede…b37b8`, nicht zum zuletzt ausgewählten Modell. Technische Exportfähigkeit ist keine Modulqualitätsfreigabe. Der bestehende generische App-ONNX-Import erwartet andere Ausgänge und wurde deshalb nicht durch bloßes Umbenennen umgangen.

## Abschluss und nächster Teil

**Technik vorhanden und geprüft, Erkennungsqualität unzureichend, neue Windows-10-Feldabnahme offen.** Kein Austausch bestehender Modelle oder Ergebnisse, keine automatische Übernahme. Der nächste konkrete Entwicklungsteil ist die Trennung vollständiger Modulinstanzen bei geeignetem nativem Bildmaßstab; zusätzliche blinde Epochen oder eine bloß größere Vorschlagsanzahl ersetzen das nicht. Erst einen tragfähigen Kandidaten einfrieren, dann unabhängige Daten prüfen und einen eigenen lokalen ROI-Bericht anbinden.

PVIS-Daten sind als CC-BY-4.0 deklariert, veröffentlichte Modell-/Referenzmetadaten als AGPL-3.0. Rechteentscheidungen für Produkt/Weitergabe bleiben getrennt und unreviewed; daraus folgt keine Produktfreigabe. Kundendaten wurden weder gelesen, exportiert noch trainiert. Private sichtbare Eckenumrisse werden nicht mit projizierten öffentlichen Ganzflächen vermischt. **Unvollständig: 280 von 287 Bildern**, eigene Thermalposen, GeoTIFF-Tags, reguläre Paarimport-Sperre und alle bisherigen Fachgrenzen bleiben erhalten.
