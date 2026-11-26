# PVIS-Referenz um eine eigene Validierungsanlage erweitern

Stand 24.11.2026 · PVIS-SPLIT-POLICY-01 real Windows10-PASS · [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Die ursprüngliche öffentliche Referenzprüfung und ihre Wiederöffnung sind laut deinen beiden Berichten bestanden:142 Bilder / 37.463 Modulbeobachtungen. **Diesen 142er-Schritt nicht wiederholen.** Die folgende Erweiterung verwendet die gespeicherten Dateien unter E:\SolarCheck-PVIS-Referenz und ergänzt ausschließlich Anlage 033. Sie benötigt dein vorhandenes App-Python, keine neue Installation. Es erscheint ein JSON-Bericht in PowerShell, kein Programmfenster.

**Abnahme abgeschlossen:** Nutzer liefert am24.11. beide inhaltlich identischen284er-Berichte, einschließlich partition_sha25661e62706…63f9dc9b. Wiederöffnung bestätigt, diesen Schritt nicht erneut ausführen.26Validierungsbilder ohne Annotationen sind erfasst, keine bestätigten Negativbilder. [Nächster Schritt: öffentlicher Bild-/Instanzmaskenadapter](PVIS_BILDADAPTER_WINDOWS10.md).

## Ganze Anlagen getrennt halten

| Anlage | Veröffentlichte Zuordnung | Lokale Aufgabe | Bilder | Modulbeobachtungen |
|---|---|---|---:|---:|
| 009 | train | Training | 58 | 16.697 |
| 033 | train | Validierung zur Modell-/Parameterwahl | 142 | 18.675 |
| 024 | test | ausschließlich spätere Abschlussprüfung | 84 | 20.766 |
| Zusammen | | drei getrennte Anlagen | 284 | 56.138 |

Anlage 033 wird aus dem veröffentlichten Trainingsbestand zurückgehalten. Ihr Originalarchiv heißt weiterhin PVDataset_train_033.zip, seine Pfade bleiben train/033. Im neuen lokalen Bericht steht **source_split=train, split=validation**. Originaldateien werden nicht umbenannt. Alle Ansichten, späteren Ausschnitte und Ableitungen einer Anlage erben denselben Datenteil. Die unterschiedlichen Bildzahlen sind beabsichtigt; kein zufälliges Aufteilen benachbarter Bilder. Prüfanlage 024 bleibt von Training und Modell-/Parameterwahl getrennt.

Das sind wiederholte Beobachtungen in Drohnen-Einzelbildern, keine 56.138 bestätigten physischen Module. Die drei ausgewählten Anlagen liegen in Ningbo. Diese kleine Aufteilung belegt keine Übertragbarkeit auf andere Städte, Kundenorthofotos oder große Solarparks.

## Festgelegter Beschriftungsvertrag

Die offizielle [PVIS-README](https://zenodo.org/records/23886365/files/README.md?download=1) beschreibt projizierte ganze Modulflächen einschließlich verdeckter Anteile. Der neue Vertrag **pvis-projected-whole-module-1** erhält diese Bedeutung:

- Veröffentlichte Polygone unverändert erhalten. Mehrere Fragmente derselben Annotation bleiben eine Instanz.
- Verdeckte Teile weder als sichtbar ausgeben noch anhand fehlender Angaben abschneiden oder ergänzen. Ihre Anzahl bleibt unbekannt; sie wird nicht als 0 ausgegeben.
- Keine automatische Umwandlung in sichtbare Modulflächen. Die manuellen, anhand sichtbarer Ecken geprüften Lernumrisse haben einen anderen Beschriftungsvertrag. Vermischung wird abgelehnt; der bestehende Lernmaskenweg akzeptiert das PVIS-Profil nicht.
- Originale Zusatzfelder sind keine bestätigten physischen Modul-IDs oder Sichtbarkeitsfreigaben. Für Instanzen immer Anlagen-/Bildbezug erhalten.

Die Aufteilung und dieser Vertrag werden gemeinsam durch **partition_sha256** gebunden. Das bestätigt die konsistente Datenbeschreibung, keine geometrische Richtigkeit oder Modellqualität. Kein DatasetBuild für echte Trainingsbilder, keine Maskenexporte und kein Trainer werden hier ausgeführt. Ein eigener öffentlicher Bild-/Instanzmaskenadapter mit festgelegter Vorverarbeitung folgt vor tatsächlichem Training.

Die Daten nennen [CC BY4.0](https://zenodo.org/records/23886365/files/LICENSE.md?download=1). Attribution/Lizenzlink/Änderungskennzeichnung bei Verwendung erhalten; Software-/Modellrechte separat behandeln. Der bestehende Rechtevertrag bleibt unreviewed. training_authorized/training_started/model_updated/production_approved bleibenfalse; keine pauschale Freigabe.

## Start ohne Installation

Zusätzlicher Download: **392.372.468Bytes, etwa392 MB**, ausschließlich die öffentliche Anlage 033. Mindestens **500 MB zusätzlich frei** im E:-Laufwerk vorsehen. Die bereits geprüften 009/024-Dateien werden lokal nachgeprüft und weiterverwendet. Die Originalarchive bleiben unverändert und komprimiert; keine Bilddekodierung, Normalisierung oder Entpackung. Kundenbilder, F:-Umgebung, SQLite und bestehende Modelle bleiben erhalten.

Den **vollständigen Block** in PowerShell ausführen:

```powershell
$ErrorActionPreference = 'Stop'
$pvSplitCommit = 'a6c1453f17f9eca35080ac0d48ddac8a173c36d1'
$pvSplitStart = Join-Path 'E:\SolarCheck-PVIS-Validierung-Start' $pvSplitCommit
New-Item -ItemType Directory -Force -Path $pvSplitStart | Out-Null
$pvSplitZip = Join-Path $pvSplitStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvSplitCommit" -OutFile $pvSplitZip
if ((Get-FileHash -Algorithm SHA256 $pvSplitZip).Hash.ToLowerInvariant() -ne '63c7c7c8cfe8c3d87dfea5fa75dee9daecd64a8963df6a6657e678cc17c08fa7') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvSplitZip -DestinationPath $pvSplitStart -Force
$pvSplitSource = Join-Path $pvSplitStart "MCM-SolarCheck-$pvSplitCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvSplitSource 'scripts\MCM_SolarCheck_PVIS_REFERENZ.py') --prefix 'E:\SolarCheck-PVIS-Referenz' --prepare-splits
```

Feste Quelle **a6c1453f17f9eca35080ac0d48ddac8a173c36d1**, QuellZIP **3220675 Bytes**, SHA256 **63c7c7c8cfe8c3d87dfea5fa75dee9daecd64a8963df6a6657e678cc17c08fa7**. Alle **692 Python-Dateien** unter src/scripts sowie **9 Konfigurations-/Paketlistendateien** mit dem remote geladenen Archiv bytegleich geprüft; finale HEAD-CI in PR9.

Erwarteter Bericht:

```json
{
  "check": "solarcheck-pvis-training-reference-1",
  "status": "partition_verified_not_training_ready",
  "images": 284,
  "annotation_observations": 56138,
  "validation_stations": 1,
  "split_images": {"train": 58, "validation": 142, "test": 84},
  "training_started": false,
  "model_updated": false
}
```

Die vollständige Ausgabe enthält zusätzlich Prüfsummen, Beschriftungsvertrag und Fachflags. **Nur den JSON-Text mitteilen**, keine Bilder. Kein neues Modell im KI-Vergleich auswählen; der Erkennungsstand wurde noch nicht verbessert.

## Gespeicherte Aufteilung wieder öffnen

Der neue Bericht heißt **training-reference.json**. Der frühere reference.json bleibt unverändert. Nach Schließen von PowerShell diesen vollständigen Befehl ausführen:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Validierung-Start\a6c1453f17f9eca35080ac0d48ddac8a173c36d1\MCM-SolarCheck-a6c1453f17f9eca35080ac0d48ddac8a173c36d1\scripts\MCM_SolarCheck_PVIS_REFERENZ.py' --prefix 'E:\SolarCheck-PVIS-Referenz' --show-splits
```

Es müssen dieselben284 Bilder / 56.138 Beobachtungen und derselbe partition_sha256 erscheinen. **--show-splits** prüft ausschließlich lokal, ohne Download oder Training. Das alte --show zeigt weiterhin den bestätigten142er-Bericht; es ist nicht der neue Wiederöffnungsbefehl.

Strg+C bricht ab und entfernt nur die eigene unvollständige Kopie. Neustart mit --prepare-splits verwendet komplette SHA-geprüfte Dateien; die unterbrochene033-Datei beginnt von vorn. Ein Rest nach hartem Beenden wird vor dem Platzbedarfstest entfernt. Ein alter vollständiger Aufteilungsbericht und der142er-Bericht bleiben bei Fehler/Abbruch erhalten. Dieselbe Prozesssperre schützt alte und neue Befehle vor parallelen Änderungen. Geänderte Pakete/Quelle/Berichte oder Labelverträge werden abgelehnt.

## Falls ein Zertifikatsfehler auftritt

TLS-Prüfung eingeschaltet lassen. Nur [PVDataset_train_033.zip](https://zenodo.org/records/23886365/files/PVDataset_train_033.zip?download=1) im Browser in einen eigenen Quellordner laden. Der Dateiname muss unverändert bleiben; die fünf Dateien des alten Imports müssen nicht erneut heruntergeladen werden.

Offizielle Identität:392372468Bytes, SHA256 **85270e796868b7a242e3f10bee15c17fcb0ff937106b49d8f22d1f53b0cb43f2**, aus dem [Anbietermanifest](https://zenodo.org/records/23886365/files/archive_manifest.csv?download=1).

```powershell
$pvValidationDownloads = Read-Host 'Vollstaendiger Pfad zum Ordner mit PVDataset_train_033.zip'
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Validierung-Start\a6c1453f17f9eca35080ac0d48ddac8a173c36d1\MCM-SolarCheck-a6c1453f17f9eca35080ac0d48ddac8a173c36d1\scripts\MCM_SolarCheck_PVIS_REFERENZ.py' --prefix 'E:\SolarCheck-PVIS-Referenz' --prepare-splits --archive-dir $pvValidationDownloads
```

Dieser Weg kopiert ausschließlich die fest gebundene033-Datei aus dem bewusst ausgewählten Quellordner. Keine Netzverbindung, keine Änderung am Originaldownload. Bei Fehler nur den Diagnoseblock als Text mitteilen; keine Neuinstallation.

## Nachweise und nächster Einstieg

116 gezielte synthetische Tests, davon 22 neue Fälle, bestanden. Trennung der Anlagen/Quellrollen, Labelvertragsgrenze, Änderungen, Abbruch/Neustart/Wiederöffnung, Quellschutz, Parallelstart und Platzmangel geprüft. Die echte öffentliche 033-Datei stimmt mit dem Anbieter-SHA überein; vollständige Erweiterung und Wiederöffnung mit **python -S** liefern denselben284er-Bericht. Keine Bildpixel dekodiert. Der alte142er-Bericht bleibt lesbar. Native Windows-CI und reale Windows-10-Bedienabnahme sind getrennte Nachweise; letztere für diese Erweiterung noch offen.

Danach den öffentlichen Bild-/Instanzmaskenadapter, eigene reproduzierbare Vorverarbeitung und Rechteentscheidung qualifizieren; anschließend begrenztes reales Training und unabhängiger Vergleich. Keine erneute CVUT-Originalprofilfreigabe, keine unveränderten PV-Hawk-Wiederholungen, keine 1000 Pflichtreviews. Thermal bleibt **unvollständig: 280 von 287 Bildern**, mit GeoTIFF-Tags und regulärer Paarimport-Sperre; keine Abdeckungs-/Geometrie-/Celsiusfreigabe.
