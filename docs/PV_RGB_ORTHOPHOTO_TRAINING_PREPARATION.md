# RGB-Orthofoto-Modulgrenzen: lokale Lern- und Prüfvorbereitung

Stand21.11.2026 · Vorbereitung real bedienbar / PV-ORTHO-TRAIN-IGNORE-01 implementiert, neue Abnahme offen · [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

**Aktueller Feldbefund20.11.:** Öffentlicher CVUT-Pilot technisch eingerichtet und real im gespeicherten RGB-Ausschnitt ausgeführt:73Kandidaten,0/8Teilreferenzen wiedergefunden, sichtbare kleine/Teilumrisse; Feldqualität FAIL. [Befund und nächster Entwicklungsblock](CVUT_PV_PILOT_WINDOWS10.md): Originaleingabe/Klassenzuordnung und öffentliche annotierte Referenzprüfung zuerst; noch keine belegte Ursache oder Korrektur. Keine unveränderte Wiederholung/Neuinstallation oder Pflicht zur manuellen Prüfung aller Module. Nachtraining mit öffentlichen Daten erst nach qualifizierter Integration. Kundendaten bleiben lokale zurückgehaltene Prüfung. Nutzer beauftragt21.11. die lokale Vorbereitung vorhandener geprüfter/korrigierter Umrisse. Kein Bildexport oder tatsächlicher Trainingsstart.

## Aktuell: nicht sichtbare Modulecken ausdrücklich ausnehmen

Nutzer bestätigt Speicherung/Wiederöffnung der Lernvorbereitung, meldet29Einträge mit teilweise nicht sichtbaren Modulecken. Das bestätigt den Bedienweg, **keine vollständig richtige Trainingsreferenz**. Mit unsicheren ganzen Umrissen noch keinen Trainingslauf starten. Die neue Ausnahmefunktion ist umgesetzt und synthetisch geprüft, ihre reale Bedienabnahme steht aus.

1. Aktualisierte Oberfläche mit dem Startblock unten öffnen → vorhandener Thermal-Lauf13.11./18:58:37/oh9ptgy5 → gespeicherter RGB-Vergleich → **PV-Modul-Entwürfe** → **Lernmuster lokal vorbereiten**. Keine neue Detektion/Matching-/Orthofotoberechnung.
2. **Unklaren Bereich markieren** öffnet den vorhandenen maximierbaren Vier-Ecken-/Zoomeditor. Einen Bereich großzügig um die gesamten unklaren Module markieren. **Keine nicht sichtbaren Modulecken erraten.** Die Ausnahmefläche behauptet keinen physischen Modulumriss. **Bereich vom Lernen ausnehmen** übernimmt sie nur in den Arbeitsstand; ursprüngliche Modulprüfung unverändert.
3. Betroffene offene/passende Vorschläge werden ganz ausgenommen, ebenso überlappende Teilumrisse. Sichere andere Umrisse bleiben Lernziele. Gelöschte/verworfene Fehlumrisse werden nicht allein durch ihren Status zu Hintergrundlabels. Weitere Bereiche bei Bedarf ergänzen; höchstens20je Ausschnitt. Verbleibende Lernziele und ausgenommene Vorschläge werden angezeigt.
4. **Lernmaske prüfen**: links ursprünglicher RGB-Ausschnitt, rechts480×270Pixel des bisherigen Kandidatenprofils. **Grün** zum Lernen ausgewählt, **Magenta** ausgenommen einschließlich Sicherheitsrand; übrige Pixel Hintergrund. U1/U2… entsprechen den Bereichen im Auswahlfeld. **Ausnahme entfernen** entfernt den gewählten Bereich im Arbeitsstand und setzt die Vollständigkeitsbox zurück.
5. Erst wenn alle sichtbaren Module korrekt beschriftet oder ausdrücklich ausgenommen sind, die neue Bestätigung aktivieren → **Lernmuster-Vorbereitung lokal speichern**. Nicht ignorierte offene/Randumrisse/Überlappungen oder RGB-NoData blockieren. NoData innerhalb expliziter Ausnahmen wird nicht Hintergrund. PV und Hintergrund müssen außerhalb der Ausnahmen auch in der Zielgröße verbleiben. Unmarkierte Module erkennt die Bestätigung nicht automatisch.
6. Schließen/wiederöffnen → Ausnahmen und Maske prüfen. Im Maskenfenster **Lernmasken-Kennzahlen kopieren(ohne Bilder und Pfade)** verwenden. Bitte nur diesen JSON-Text mitteilen, keine Bilder oder privaten Berichte. Er nennt den Datenteil; eine Anlage/Gruppe bleibt zusammen und ersetzt kein unabhängiges Prüfset.

Alte Schema1-Vorbereitungen bleiben lesbar; ihre Vollständigkeitsbox ist für die neue Maskenprüfung zunächst **nicht** markiert. Nach Sichtprüfung/Ausnahmen bewusst neu bestätigen. Speicherung verwendet Schema2; ältere Oberflächen dürfen diese Datei nicht überschreiben. Schließen/Abbrechen ohne Speichern verändert den vorherigen Stand nicht. Modul-/Ausnahmeänderungen erfordern erneute Bestätigung. **Vollständigkeitsbestätigung zurücknehmen** entfernt die gewählte Vorbereitung einschließlich ihrer gespeicherten Ausnahmeflächen; die Modul-Entwürfe bleiben erhalten.

### Vertrag zur späteren Trainingsanbindung

Die nur im Arbeitsspeicher erzeugte Klassenmaske hat **0=Hintergrund,1=PV,255=Ignorieren**. Ausnahmen werden um einen nativen Pixel erweitert und beim Verkleinern konservativ erhalten, damit kleine unklare Flächen nicht versehentlich Hintergrund werden. Der räumliche Index führt mask_policy, ignore_polygons_px und ignore_value=255zusätzlich zum source_window mit. Ein künftiger Trainer muss die Maske mit **ignore_index=255** verwenden; nicht nur positive Polygone als vollständiges Hintergrundbild rasterisieren. CPU-Autograd mit PyTorch2.15.0 synthetisch geprüft: Ignorierpixel haben null Gradienten, PV-/Hintergrundpixel tragen bei. Das ist ein Loss-Vertragsnachweis, kein Kundentrainingslauf oder fertig qualifizierter PV-Trainer.

122gezielte synthetische Regressionen inkl.20neuer Backend-/GUI-Fälle und10isolierte echte Torch-/Referenztests bestanden. Vorschau/Kennzahlen sind keine Modellvorhersage oder Bestätigung des originalen CVUT-Eingabeprofils. Anbieterabruf21.11.502; keine Vorverarbeitung/Schwellen/Gewichte auf Verdacht geändert. Altdaten-Tests lesen/schreiben UTF-8 ausdrücklich, einschließlich Umlauten; ein abgebrochener Dialogaufbau lässt sich sicher schließen. Keine neue Software, kein Bildexport/Modellwechsel oder produktiver DB-Eingriff; training_authorized/training_started/images_exported/model_updated und Fachflags false. Originalprofil, Trainer, Nutzungsrechte/Zustimmung und unabhängiges Prüfset vor echtem Training offen. Wenige geeignete Ausschnitte statt1000Pflichtreviews. Kundendaten lokal, unvollständig280/287/GeoTIFF-Tags/Paarimport-Sperre erhalten.

## Aktueller Start ohne Installation

Alte SolarCheck-Vergleichsfenster schließen, anschließend diesen gesamten Block in **PowerShell** ausführen. Er lädt ausschließlich eine fest geprüfte Quellcode-ZIP(ca.3MiB) in einen neuen E:-Startordner und startet die Oberfläche mit dem bereits vorhandenen F:-Python. Keine Pakete/Modelle/Gewichte herunterladen oder neu einrichten. Bestehende CVUT-/PV-Hawk-Umgebungen, Quellen und Projektdateien bleiben erhalten. Der Starter öffnet die Oberfläche; er beginnt kein Training.

```powershell
$ErrorActionPreference = 'Stop'
$pvLearnCommit = 'e5ce87f716f00612a91b22d9b372f499d40f9786'
$pvLearnStart = Join-Path 'E:\SolarCheck-Lernmuster-Start' $pvLearnCommit
New-Item -ItemType Directory -Force -Path $pvLearnStart | Out-Null
$pvLearnZip = Join-Path $pvLearnStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvLearnCommit" -OutFile $pvLearnZip
if ((Get-FileHash -Algorithm SHA256 $pvLearnZip).Hash.ToLowerInvariant() -ne 'dbeefdc634a4b06a0b4ae9e0bd2d2cd56b83da518e8161580d7d9110e012be57') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvLearnZip -DestinationPath $pvLearnStart -Force
$pvLearnSource = Join-Path $pvLearnStart "MCM-SolarCheck-$pvLearnCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvLearnSource 'scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py')
```

Feste Quelle **e5ce87f716f00612a91b22d9b372f499d40f9786**, ZIP **3161628Bytes**, SHA256 **dbeefdc634a4b06a0b4ae9e0bd2d2cd56b83da518e8161580d7d9110e012be57**. Alle **688Python-Dateien unter src/scripts** sowie bestehende CVUT-Konfiguration/Paketlisten mit dem remote geladenen Archiv bytegleich geprüft. Für diesen Bedienweg kein Git-Checkout und kein neues Installationsprogramm nötig. Spätere Dokumentationsnachträge ändern diese Laufzeitquelle nicht.

**Später nur Oberfläche öffnen, ohne erneuten Download:**

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-Lernmuster-Start\e5ce87f716f00612a91b22d9b372f499d40f9786\MCM-SolarCheck-e5ce87f716f00612a91b22d9b372f499d40f9786\scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py'
```

## Neuer Bedienweg21.11.: vorhandene Umrisse als Lernmuster vorbereiten

Passende, korrigierte und ergänzte Umrisse müssen nicht neu gezeichnet werden. Verwendet wird ausschließlich die **zuletzt gespeicherte** Modulprüfung. Alle Aktionen bleiben lokal; Codex verwendet ausschließlich Code und synthetische Raster.

1. Aktualisierte Oberfläche → vorhandener Thermal-Lauf13.11./18:58:37/oh9ptgy5 → gespeicherter RGB-Vergleich → **PV-Modul-Entwürfe**. Keine neue Rekonstruktion/KI-Berechnung nötig.
2. Wenige kleine geeignete RGB-Ausschnitte vollständig beschriften: passende ganze Module behalten, fehlende ergänzen, falsche verwerfen/löschen. Alle verbleibenden ganzen Module als **Umriss passt** beurteilen → **Modul-Entwürfe und Prüfung lokal speichern**. Offene Umrisse, erhebliche Überlappungen (auch sehr kleine Teilumrisse innerhalb ganzer Module), Randumrisse oder RGB-NoData blockieren. Bei angeschnittenen/unklaren Modulen zunächst die Ausnahmefunktion oben verwenden; keine unsichtbaren Ecken ergänzen.
3. **Lernmuster lokal vorbereiten** → lokale **Anlagengruppe** und **Geprüft von** eintragen. Dieselbe Anlage und zusammengehörige Befliegungen auch bei anderen Orthofotos immer gleich benennen. Alle Ausschnitte eines Orthofotos behalten dieselbe Gruppe; Groß-/Kleinschreibung/Leerzeichen werden vereinheitlicht.
4. Erst nach vollständiger Sichtprüfung **Alle sichtbaren Module korrekt umrandet oder ausdrücklich vom Lernen ausgenommen** → **Lernmuster-Vorbereitung lokal speichern**. Eine menschliche Beschriftungsbestätigung erkennt fehlende Module nicht automatisch und bestätigt keine physische Modul-ID, Geometrie, Thermalabdeckung oder Celsiuswerte.
5. Ergebnis zeigt Modulflächenzahl und festen Datenteil der Gruppe: Training, Validierung oder unabhängige Prüfung. Wiederöffnung lädt ohne Inferenz. Bestehender80/10/10-Gruppenmechanismus hält korrelierte Ausschnitte zusammen; Gruppe nicht zum Erzwingen eines anderen Datenteils umbenennen. Ein Orthofoto/eine Gruppe ergibt **kein unabhängiges Prüfset oder vollständigen Trainingsdatensatz**.
6. Nach gespeicherten Moduländerungen erscheint **Vorbereitung veraltet**; erneut prüfen/bestätigen. **Vollständigkeitsbestätigung zurücknehmen** entfernt nur diese Vorbereitung; Modulprüfung und andere Ausschnitte bleiben. Schließen ohne Speichern ändert nichts.

**pv-learning-preparation.LOCAL.json** enthält lokale Geometrien/Metadaten mit Quell-, Review- und Snapshot-Hashes. Nur aktuelle passende Umrisse werden positive **pv_module**-Labels; Historie/verworfene/gelöschte Umrisse keine Trainingsziele. Insbesondere gelöschte kleine Rechtecke innerhalb richtiger Module sind keine Hintergrundlabels. RGB-Fensterkoordinaten und exaktes **source_window** bleiben zusammen; ein späterer Export muss genau diesen Bildausschnitt lesen, nicht das ganze TIFF mit lokalen Polygonkoordinaten verwenden.

Kein Bildexport, Trainer-/Modellimport, Training, Modellwechsel, Installation oder SQLite-Eingriff. **training_authorized=false** bleibt bestehen. Nutzungsrechte/Zustimmung, geeigneter Trainer und das tatsächliche Eingabe-/Klassenprofil sind vor echtem Training separat zu belegen; bestehende Einwilligungs-/Trainingsarchitektur bleibt erhalten. Abbruch oder konkurrierende Quell-/Review-/Speicheränderung erhalten die vorherige Vorbereitung.84gezielte synthetische Regressionen inkl.20neuer Backend-/GUI-Fälle bestanden. Neue GUI-Tests verwenden die vorhandene Qt-Aufräumfixture und zerstören Fenster noch bei lebender QApplication;27Lebenszyklusregressionen bestanden. Finaler Gesamtprozess muss einschließlich Interpreterende sauber enden; exakte HEAD-CI in PR9. Laufzeitquellee5ce87f7 unverändert. Reale Windows10-Bedienabnahme offen. Noch keine verbesserte Erkennung durch diese Vorbereitung.

## Hinweise aus den Nutzerquellen21.11.

Der [Bayern-Beitrag](https://geodaesie.info/images/zfv/150-jahrgang-2025/downloads/zfv_2025_2_Kraus_et-al.pdf) liefert Hinweise auf auflösungsabhängige Modelle, überlappende Kacheln und unabhängige Testregionen. Binäre PV-Flächenmasken und Parkerkennung belegen keine fehlerfreie Einzelmodulerkennung; Dachausschluss und8m²-Flächenfilter nicht übernehmen. Erster/dritter Nutzerlink dieselbe Veröffentlichung. Keine direkt nutzbaren Gewichte samt dokumentiertem Ladeweg in den verlinkten Quellen gefunden. Bildmaßstab/Seitenverhältnis bleiben CVUT-Prüfhypothesen, keine belegte Fehlerursache. Der [OST-PV-Quicktest](https://www.ost.ch/fileadmin/dateiliste/3_forschung_dienstleistung/institute/spf/news/2025/0210_pv-modulanalyse/2025-02_eeu-newsletter_pv-quicktest.pdf) klassifiziert Solarzellen in Elektrolumineszenzbildern, kein direkter Drohnen-RGB-/Thermal-Moduldetektor. Keine neue Software daraus installiert.

## Historischer Befund und Entscheidung

Die korrigierte PVConfigRGB-Eingabe wird real verwendet. Die technische Integration liefert jetzt Vorschläge; die Qualität reicht für zuverlässige automatische Auswertung noch nicht. Die bisherigen Modellläufe sind Inferenz mit unveränderten Gewichten und lernen nicht selbstständig aus Korrekturen.

| Beobachtung im lokalen Pilot | Aussage |
|---|---|
|21Modellinstanzen,18endgültige Vorschläge|Eine geteilte Maske und zwei Randfälle ausgeschlossen; alle18passieren weitere Filter.|
|740Regionen,86Vordergrund,30ab0,7,4ab0,9|maximal0,9547ist Modellkonfidenz, keine belegte Genauigkeit; Regionen sind keine Module.|
|Drei von acht gespeicherten Vergleichsumrissen wiedergefunden|Fünf dieser Teilreferenzen fehlen im Vergleich. Keine globale Vollständigkeitsquote.|
|15weitere ungeprüfte Kandidaten|Nicht pauschal15Fehler: außerhalb der gelben Teilreferenz können echte Module liegen.|
|Teilmodule/versetzte grüne Umrisse|Die vortrainierte Erkennung ist noch nicht ausreichend auf diesen Orthofoto-Fall übertragbar. Ein Datendomänenunterschied ist plausibel, aus einem Ausschnitt aber nicht vollständig bewiesen.|

Keine weitere unveränderte Wiederholung, künstliche Modulanhebung nach erwarteter Anzahl oder blindes Senken der Konfidenz. Die drei ausgeschlossenen Instanzen erklären nicht die sichtbaren Qualitätsprobleme. Bestehende Entwürfe/Originale/GeoTIFFs erhalten, KI-Vorschläge weiter ungeprüft und separat.

## Begrenzter nächster Nutzerweg mit bestehender Oberfläche

1. Gespeicherten RGB-/Thermal-Vergleich → PV-Modul-Entwürfe öffnen. Keine neue Rekonstruktion/Installation und keine weitere KI-Inferenz erforderlich.
2. Mit wenigen kleinen, unterschiedlichen RGB-Ausschnitten beginnen: klare Module, Schatten/Reflexionen, unterschiedliche Ausrichtung oder Dach-/Reihensituation. Das ist eine einmalige repräsentative Stichprobe, keine Vorgabe1000Produktionsmodule einzeln freizugeben. Die tatsächlich nötige Datenmenge ist noch nicht bestimmt.
3. Jeden gewählten Ausschnitt vollständig beschriften: alle vollständig sichtbaren Module als ganze Flächen umreißen; passende Umrisse beibehalten, falsche/zu kleine verwerfen oder mit vier Ecken korrigieren, fehlende ergänzen. Vorhandenen maximierbaren Editor/Zoom und lokales Speichern/Wiederöffnen nutzen. Rand-/angeschnittene oder unklare Module gesondert behandeln, nicht als vollständige positive Modulmaske ausgeben.
4. Speicherung bleibt bei lokalen Entwurfs-IDs und ungeprüften Fach-/Geometrie-/Temperaturflags. Ein korrekt beurteilter Bildumriss bestätigt keine physische Anlagen-ID/Thermalabdeckung. Bilder, Koordinaten und pv-modules.LOCAL.json bleiben lokal.

**Die acht bisherigen Referenzen sind keine vollständige Trainingsannotation für den größeren Ausschnitt.** Ein Instanztrainer könnte alle weiteren sichtbaren, unmarkierten Module als Hintergrund lernen. Deshalb keine direkte Übernahme der18KI-Kandidaten oder Export der acht Referenzen als vollständiger Datensatz. Ein Ausschnitt darf erst nach expliziter Vollständigkeitsprüfung als Trainingsbeispiel gelten. Die neue Vorbereitung speichert eine ausdrückliche menschliche Bestätigung revisionsgebunden; eine freie Notiz genügt nicht.

## Bestand und konkrete Verbindung

| Vorhanden | Wiederverwendung / offene Verbindung |
|---|---|
|services/thermal_partial_pv.py und gui/thermal_partial_pv.py|Bestehende lokale Korrektur/Prüfung verwenden. Einwilligung und vollständige Annotation nicht aus outline_ok einzelner Module ableiten.|
|review/training_geometry.py: ReviewedGeometry/Polygon-/Grenzprüfung|Native RGB-Ecken in Pixelkoordinaten des exakten Ausschnitts übertragen; Darstellung/Größe prüfen. Keine Thermalwerte als RGB-Labels.|
|review/training_export.py: build_spatial_training_index|Backendneutraler räumlicher Export aus geprüftem Snapshot vorhanden. Lokale Snapshot-/Fenster-Brücke vorbereitet; tatsächlicher RGB-Crop-/Maskenexport und Trainer bleiben offen.|
|review/training_split.py: Gruppenbindung|Gleiche Anlage/Quelle, überlappende Ausschnitte und gleiche Module nicht über Training/Prüfung verteilen. Ausschnitt-Entwurfs-IDs sind keine globalen physischen IDs und verhindern Datenleckage nicht allein.|
|review/training_snapshot.py / training_runner.py / model_lineage.py|Prüfsummen, reproduzierbarer Snapshot, Trainingsherkunft/neues Gewichtsartefakt und getrennte spätere Registrierung wiederverwenden. Ein injizierbarer Trainer ist noch kein qualifizierter Backend.|
|OfflineTrainingJobs + offline_training_preflight.py|Desktop-Ausführung derzeit Bildklassifikation, kein fertiger PV-Hawk-Modul-Instanz-/Maskentrainer. Nicht mit Polygonen füttern oder als solchen freischalten.|
|Optionaler review/ultralytics_training.py-Adapter|Keine automatische Installation/Übernahme. Code-/Gewichts-/Datenrechte getrennt prüfen; keine AGPL-/Enterprise-Entscheidung aus vorhandener Adapterklasse ableiten.|
|TrainingConsentService und Zustimmungs-/Snapshot-/Staging-Bausteine|Vor tatsächlicher Trainingsnutzung/Bildexport aktive passende Zustimmung und Rechte prüfen. Technischer PV-Hawk-Evaluationspilot keine pauschale Zustimmung zum Training mit Kundenbildern.|

Der implementierte Block verbindet **vollständig geprüfte kleine RGB-Ausschnitte → bestehende räumliche Geometrie/Snapshot/Split-Verträge → lokale Vorbereitungsanzeige**. Noch keinen automatischen Bildexport, Training oder neues Modell aktivieren. Codex weiterhin ausschließlich Quellcode/synthetische Tests; reale Auswahl/Verarbeitung bewusst lokal durch Nutzer.

## Trainingspilot und Abnahme danach

Passenden Instanztrainer erst konkret qualifizieren: vorhandene PV-Hawk-Gewichte/MIT-Code als Ausgangspunkt prüfen, vollständige Trainingskompatibilität/Abhängigkeiten/Windows10-CPU- bzw. GPU-Zeit und Speicher gesondert belegen. Erfolgreiche Inferenz beweist keine funktionierende Trainingsschleife. Keine neue Software automatisch installieren, unbekannte Gewichtsformate ausführen oder produktive Gewichte überschreiben.

Vor Training: vollständige geprüfte Annotationen, passende Datennutzungsrechte/Zustimmung, unveränderlicher Snapshot, begrenzter Lauf und festes unabhängiges Prüfset. Neue Gewichte getrennt speichern, Rückkehr zum Ausgangsmodell behalten. Ein Standort allein bestätigt keine Übertragbarkeit auf andere Anlagen.

Vorher/nachher auf demselben vorher zurückgehaltenen Prüfset messen: verpasste Module, falsche Zusatzumrisse, Teilmodule/Dubletten, Lage der Modulgrenzen, verbleibender manueller Prüfaufwand und Laufzeit. Gleiche/überlappende Module nicht in Training und Test; Trainingserfolg auf denselben Bildern reicht nicht. Vorhandene Korrekturen bilden später den Ausnahmeweg, nicht1000obligatorische Einzelprüfungen. Ergänzende Größen-/Form-/Reihenprüfungen können unplausible Vorschläge markieren, ersetzen fehlende Erkennung nicht.

**Status:** Vorbereitung implementiert/synthetisch geprüft, reale Bedienabnahme offen. Noch kein Instanztrainer oder tatsächlicher Bildexport; keine Kundenbilder hier gelesen und kein Training/Modellwechsel gestartet. Keine belegte Verbesserung durch Nachtraining oder Gesamtanlagenfreigabe. Dauerlabel „unvollständig: 280 von 287 Bildern“/GeoTIFF-Tags, reguläre Paarimport-Sperre und alle False-Freigaben bleiben.
