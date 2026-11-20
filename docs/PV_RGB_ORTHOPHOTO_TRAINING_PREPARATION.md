# RGB-Orthofoto-Modulgrenzen: lokale Lern- und Prüfvorbereitung

Stand19.11.2026 · PV-HAWK-FIELD-QUALITY-01 / PV-ORTHO-TRAIN-PREP-01 · [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

**Aktueller Feldbefund20.11.:** Öffentlicher CVUT-Pilot technisch eingerichtet und real im gespeicherten RGB-Ausschnitt ausgeführt:73Kandidaten,0/8Teilreferenzen wiedergefunden, sichtbare kleine/Teilumrisse; Feldqualität FAIL. [Befund und nächster Entwicklungsblock](CVUT_PV_PILOT_WINDOWS10.md): Originaleingabe/Klassenzuordnung und öffentliche annotierte Referenzprüfung zuerst; noch keine belegte Ursache oder Korrektur. Keine unveränderte Wiederholung/Neuinstallation oder Pflicht zur manuellen Prüfung aller Module. Nachtraining mit öffentlichen Daten erst nach qualifizierter Integration. Kundendaten bleiben lokale zurückgehaltene Prüfung. Nachfolgende Labelvorbereitung bleibt Hintergrund, kein Auftrag zum Export privater Bilder.

## Befund und Entscheidung

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

**Die acht bisherigen Referenzen sind keine vollständige Trainingsannotation für den größeren Ausschnitt.** Ein Instanztrainer könnte alle weiteren sichtbaren, unmarkierten Module als Hintergrund lernen. Deshalb keine direkte Übernahme der18KI-Kandidaten oder Export der acht Referenzen als vollständiger Datensatz. Ein Ausschnitt darf erst nach expliziter Vollständigkeitsprüfung als Trainingsbeispiel gelten. Die heutige Software speichert diese Bestätigung noch nicht als eigenes Trainingsmerkmal; eine freie Notiz ist kein maschinengeprüfter Ersatz.

## Bestand und konkrete Verbindung

| Vorhanden | Wiederverwendung / offene Verbindung |
|---|---|
|services/thermal_partial_pv.py und gui/thermal_partial_pv.py|Bestehende lokale Korrektur/Prüfung verwenden. Einwilligung und vollständige Annotation nicht aus outline_ok einzelner Module ableiten.|
|review/training_geometry.py: ReviewedGeometry/Polygon-/Grenzprüfung|Native RGB-Ecken in Pixelkoordinaten des exakten Ausschnitts übertragen; Darstellung/Größe prüfen. Keine Thermalwerte als RGB-Labels.|
|review/training_export.py: build_spatial_training_index|Backendneutraler räumlicher Export aus geprüftem Snapshot vorhanden. Bridge vom lokalen Orthofoto-ROI/Entwurfsformat fehlt; keine zweite Geometrie-/Datenbankarchitektur bauen.|
|review/training_split.py: Gruppenbindung|Gleiche Anlage/Quelle, überlappende Ausschnitte und gleiche Module nicht über Training/Prüfung verteilen. Ausschnitt-Entwurfs-IDs sind keine globalen physischen IDs und verhindern Datenleckage nicht allein.|
|review/training_snapshot.py / training_runner.py / model_lineage.py|Prüfsummen, reproduzierbarer Snapshot, Trainingsherkunft/neues Gewichtsartefakt und getrennte spätere Registrierung wiederverwenden. Ein injizierbarer Trainer ist noch kein qualifizierter Backend.|
|OfflineTrainingJobs + offline_training_preflight.py|Desktop-Ausführung derzeit Bildklassifikation, kein fertiger PV-Hawk-Modul-Instanz-/Maskentrainer. Nicht mit Polygonen füttern oder als solchen freischalten.|
|Optionaler review/ultralytics_training.py-Adapter|Keine automatische Installation/Übernahme. Code-/Gewichts-/Datenrechte getrennt prüfen; keine AGPL-/Enterprise-Entscheidung aus vorhandener Adapterklasse ableiten.|
|TrainingConsentService und Zustimmungs-/Snapshot-/Staging-Bausteine|Vor tatsächlicher Trainingsnutzung/Bildexport aktive passende Zustimmung und Rechte prüfen. Technischer PV-Hawk-Evaluationspilot keine pauschale Zustimmung zum Training mit Kundenbildern.|

Der nächste implementierbare Block verbindet **vollständig geprüfte kleine RGB-Ausschnitte → bestehende räumliche Geometrie/Snapshot/Split-Verträge → lokale Bereitschaftsanzeige**. Noch keinen automatischen Bildexport, Training oder neues Modell aktivieren. Codex weiterhin ausschließlich Quellcode/synthetische Tests; reale Auswahl/Verarbeitung bewusst lokal durch Nutzer.

## Trainingspilot und Abnahme danach

Passenden Instanztrainer erst konkret qualifizieren: vorhandene PV-Hawk-Gewichte/MIT-Code als Ausgangspunkt prüfen, vollständige Trainingskompatibilität/Abhängigkeiten/Windows10-CPU- bzw. GPU-Zeit und Speicher gesondert belegen. Erfolgreiche Inferenz beweist keine funktionierende Trainingsschleife. Keine neue Software automatisch installieren, unbekannte Gewichtsformate ausführen oder produktive Gewichte überschreiben.

Vor Training: vollständige geprüfte Annotationen, passende Datennutzungsrechte/Zustimmung, unveränderlicher Snapshot, begrenzter Lauf und festes unabhängiges Prüfset. Neue Gewichte getrennt speichern, Rückkehr zum Ausgangsmodell behalten. Ein Standort allein bestätigt keine Übertragbarkeit auf andere Anlagen.

Vorher/nachher auf demselben vorher zurückgehaltenen Prüfset messen: verpasste Module, falsche Zusatzumrisse, Teilmodule/Dubletten, Lage der Modulgrenzen, verbleibender manueller Prüfaufwand und Laufzeit. Gleiche/überlappende Module nicht in Training und Test; Trainingserfolg auf denselben Bildern reicht nicht. Vorhandene Korrekturen bilden später den Ausnahmeweg, nicht1000obligatorische Einzelprüfungen. Ergänzende Größen-/Form-/Reihenprüfungen können unplausible Vorschläge markieren, ersetzen fehlende Erkennung nicht.

**Status:** Bestandsprüfung und konkreter Vorbereitungsschritt dokumentiert. Keine neue Trainingsfunktion implementiert, Kundenbilder exportiert/gelesen oder Training/Download/Modellwechsel gestartet. Keine belegte Verbesserung durch Nachtraining oder Gesamtanlagenfreigabe. Dauerlabel „unvollständig: 280 von 287 Bildern“/GeoTIFF-Tags, reguläre Paarimport-Sperre und alle False-Freigaben bleiben.
