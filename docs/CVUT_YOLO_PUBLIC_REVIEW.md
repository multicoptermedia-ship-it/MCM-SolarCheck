# CVUT-YOLO: öffentlicher Erkennungsbefund vom 27.11.2026

Das bereitgestellte Paket enthält vortrainierte RGB-Modellgewichte. Der Zugriff ist gelöst. Die öffentliche Prüfung belegt einen Fortschritt bei den PV-Flächen, aber noch keine brauchbare automatische Modulzählung. Dafür ist **kein neuer Installations- oder unveränderter Wiederholungslauf beim Nutzer** erforderlich.

## Aktueller Fortsetzungspunkt: CVUT-YOLO-NATIVE-01

Die nachgelagerte Umrissprüfung enthielt eine unpassende Annahme: Das Seitenverhältnis eines Moduls wurde im Bild auf 1,25 bis 2,8 begrenzt. Bei projizierten, schräg gesehenen Flächen ist dieses Verhältnis kein festes physisches Modulmaß. Schon **60 von 117 Referenzumrissen** fallen außerhalb dieser Grenze. Außerdem kann ein ganzes Modul einen engen gewählten Ausschnitt großteils ausfüllen.

Der eigene Forschungs-Viereckpfad verwendet die Hülle aller Maskenteile derselben vorhergesagten Instanz und eine OpenCV-Polygonannäherung mit zwei Prozent Umfangstoleranz; wenn kein konvexes Viereck entsteht, ein minimales umschließendes Rechteck. Keine Vermischung verschiedener Instanzen und keine Referenzmaske beim Umrissbilden. Mindestfläche/Füllung, Rand-, Geometrie- und Dublettenprüfung bleiben. Die größere erlaubte ROI-Fläche wird ausdrücklich nur für diesen Profilaufruf gewählt; die Standarddetektoren behalten ihre bisherige Maximalfläche von 20 Prozent.

**Gleiche Gewichte, gleiche 24 Ausschnitte, gleiche 117 Referenzbeobachtungen, kein weiteres Training:**

| Auswertung auf dem gespeicherten 256er Referenzraster | Treffer | Zusätzliche Vorschläge | Fehlend |
| --- | ---: | ---: | ---: |
| Bisheriger Umrisspfad, exakt reproduziert | 59 | 45 | 58 |
| Neuer Viereckpfad | **85** | **62** | **32** |

Die Korrektur liefert 26 zusätzliche Treffer und 26 weniger fehlende Module, zugleich 17 zusätzliche Vorschläge mehr. Das ist eine messbare Verbesserung, weiterhin keine ausreichende automatische Anlagenzählung oder unabhängige Genauigkeitsfreigabe.

Der Eingabemaßstab wurde separat geprüft: Das vorhandene öffentliche 033-Archiv wurde vollständig gegen die Anbieter-SHA geprüft. Nur die bisherigen 24 Ausschnitte wurden mit dem unveränderten ursprünglichen Adapter in nativen 512 Pixeln im RAM rekonstruiert. Originalrecord, native RGB-/Instanzhashs und die exakte bisherige 2×2-Reduktion stimmen für jeden Ausschnitt überein. Keine neuen Daten/Splits, kein Download, kein Pixelcache, keine Testanlage 024. Dieselben Gewichte `d80be7a0…cdc27` bleiben erhalten.

| Vergleich auf **gemeinsamem nativen 512er Referenzraster** | Treffer | Zusätzliche Vorschläge | Fehlend |
| --- | ---: | ---: | ---: |
| 256er Eingabe, Viereckmasken per nächstem Nachbarn auf512 | 85 | 66 | 32 |
| Direkte native512-Eingabe, gleicher Viereckpfad | 69 | 136 | 48 |

Die größere Eingabe verschlechtert dieses Modell. Die vier zusätzlichen Vorschläge beim Vergleichsraster512 gegenüber dem gespeicherten Raster256 entstehen durch die dort andere konservative Ignore-Abgrenzung. Diese Zahlen dürfen nicht als vier neu erzeugte Erkennungen oder als zusätzliche Modellverbesserung interpretiert werden.

[Gespeicherter vollständiger Vergleich](evidence/cvut-yolo-native-comparison-2026-11-27.json): Bericht-SHA `c84e6dd16cf324f74d5b832442a4d34b46d296e07cb0b8d1df78ca11ee3c8b8c`, elf zum ausgeführten Quellstand passende SHA, Wiederöffnung im App-Python exakt gleich. Der bestehende Prüfeinstieg bietet dafür optional `--compare-native-source <vorhandener öffentlicher PVIS-Ordner>`. Er schreibt einen neuen Bericht vom Typ `solarcheck-cvut-yolo-native-comparison-1`, überschreibt keine Altberichte und startet weder Training noch Installation. Abbruch und Quellen-/Reduktionsabweichung veröffentlichen keinen fertigen Teilbericht. Die Masken-/Modellberechnung bekommt keine Referenzumrisse oder Referenzanzahl.

Ohne Modell, Torch, Bilddekodierung oder neuen Versuch lässt sich der gespeicherte Vergleich öffnen:

```powershell
python .\scripts\MCM_SolarCheck_CVUT_YOLO_PRUEFUNG.py --show .\docs\evidence\cvut-yolo-native-comparison-2026-11-27.json
```

Dies ist kein notwendiger neuer Nutzerlauf. Der nächste Entwicklungsabschnitt untersucht gezielt die zusätzlichen und fehlenden Instanzen an öffentlichen schwierigen Beispielen. Keine weitere blinde Vergrößerung oder unveränderte Trainingswiederholung. Testanlage024 und alle Kundenbilder bleiben unangetastet; noch keine GUI-Modellübernahme oder neue Windows-10-Feldabnahme.

## Vorlauf: CVUT-YOLO-PUBLIC-01

Die folgenden Eingangsdaten und Versuche dokumentieren den unveränderten Vorlauf. Für die aktuelle Umrissprüfung gelten die beiden Tabellen oben.

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

## Historischer Abschluss von PUBLIC-01

**Technik vorhanden und geprüft, Erkennungsqualität unzureichend, neue Windows-10-Feldabnahme offen.** Kein Austausch bestehender Modelle oder Ergebnisse, keine automatische Übernahme. Der damals nächste Entwicklungsteil war die Trennung vollständiger Modulinstanzen bei geeignetem nativem Bildmaßstab; zusätzliche blinde Epochen oder eine bloß größere Vorschlagsanzahl ersetzen das nicht. Erst einen tragfähigen Kandidaten einfrieren, dann unabhängige Daten prüfen und einen eigenen lokalen ROI-Bericht anbinden.

PVIS-Daten sind als CC-BY-4.0 deklariert, veröffentlichte Modell-/Referenzmetadaten als AGPL-3.0. Rechteentscheidungen für Produkt/Weitergabe bleiben getrennt und unreviewed; daraus folgt keine Produktfreigabe. Kundendaten wurden weder gelesen, exportiert noch trainiert. Private sichtbare Eckenumrisse werden nicht mit projizierten öffentlichen Ganzflächen vermischt. **Unvollständig: 280 von 287 Bildern**, eigene Thermalposen, GeoTIFF-Tags, reguläre Paarimport-Sperre und alle bisherigen Fachgrenzen bleiben erhalten.

Vorherige Prüfsquelle (PUBLIC-01): `ac87307105e006ef5b303adb4e1c93ff0119779a`, [Quell-ZIP](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/archive/ac87307105e006ef5b303adb4e1c93ff0119779a.zip), 3402970 Bytes, SHA256 `07e18b14d43513ade78cb2b535cb5cfe6e7734a4c0e21beca0164eacede3aea9`. Alle 708 Runtime-Python-Dateien und zehn Konfigurations-/Paketlisten nach dem Download bytegleich geprüft. Lokal 71 neue synthetische Vertragsfälle und sieben echte CPU-Referenzfälle bestanden; beide Handoff-Tests zusätzlich grün. Vollständige Regression und neue Windows-Referenzprüfung am abschließenden HEAD separat in Draft PR #9 belegen.

Native-Prüfsquelle: `5cda748107cb3f4ff33766034abc88e227f6a8bf`, [Quell-ZIP](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/archive/5cda748107cb3f4ff33766034abc88e227f6a8bf.zip), 3425736 Bytes, SHA256 `218f75a3bcde2857e82ea618e661e0f46613fa6323edc350d3cce7ec33bdbff2`. Alle 711 Runtime-Dateien und zehn Konfigurations-/Paketlisten remote bytegleich. 30 neue synthetische Fälle plus ein zusätzlicher echter CPU-512-Fall bestanden; acht echte CPU-Referenzfälle insgesamt. Neue exakte HEAD-CI mit vollständiger Regression separat in Draft PR #9 belegen.
