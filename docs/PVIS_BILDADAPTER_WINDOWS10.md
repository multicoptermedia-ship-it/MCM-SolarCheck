# Öffentliche RGB-Bilder und Instanzmasken prüfen

**Reale Windows10-Abnahme26.11.2026 abgeschlossen:** Bericht, Wiederöffnung und beide Kontrollbilder laut Nutzer plausibel. Nicht erneut ausführen. Weiter mit dem [begrenzten öffentlichen Trainingspilot](PVIS_TRAININGSPILOT_WINDOWS10.md). Die folgende Adapteranleitung bleibt als Nachweis erhalten.

Stand 26.11.2026 · PVIS-IMAGE-ADAPTER-01 · [aktueller Entwicklungsstand](AKTUELLER_ENTWICKLUNGSSTAND.md).

Deine beiden Berichte bestätigen die gespeicherte Aufteilung und Wiederöffnung: 58 Trainingsbilder aus Anlage 009, 142 Validierungsbilder aus 033, 84 Prüfbilder aus 024. **Die Referenz- und Aufteilungsschritte nicht wiederholen.** Dieser neue Schritt lädt die vorhandenen öffentlichen JPEGs tatsächlich als RGB-Pixel und erzeugt begrenzte Instanzmasken im Speicher. Er startet kein Training und verändert kein Erkennungsmodell.

Der Adapter verwendet Pillow, NumPy, OpenCV und Rasterio aus deiner vorhandenen SolarCheck-App. **Keine Installation und kein erneuter Datensatzdownload.** Nur die feste Quellcode-ZIP für diesen neuen Schritt wird geladen. Vorhandenes F:-Python und gespeicherte öffentliche ZIPs unter E:\SolarCheck-PVIS-Referenz weiterverwenden. Etwa 50 MB freier Platz für Bildprotokolle und zwei öffentliche Kontrollbilder reichen; die Originalbilder werden nicht entpackt oder überschrieben.

## Was geprüft wird

- JPEGs einzeln vollständig dekodieren, RGB und Maße gegen COCO prüfen. Prüfanlage 024 wird dabei nicht als Bild geöffnet. Seine Paketidentität und reservierte Zuordnung bleiben geprüft.
- Ein deterministischer nativer 512×512-Ausschnitt je Trainings-/Validierungsbild: bevorzugt um die erste ausreichend vollständige Modulannotation, sonst Bildmitte. Kein Strecken, keine Perspektivkorrektur oder Belichtungsänderung. Die Skalierung RGB→float32/CHW/255 ist nur ein eigener numerischer Eingabevertrag, keine Bestätigung der originalen CVUT-Vorverarbeitung.
- Vorhandenen GDAL-Rasterer verwenden; COCO-Eckkoordinaten ausdrücklich auf dessen Pixelmitten-Abtastung abbilden. Publizierte area-Werte sind keine Prüfsummen dieser Rasterisierung; Rasterer/Version werden festgehalten.
- Jedes Modul bleibt eine eigene Instanz, mehrere Fragmente einer Annotation bleiben zusammen. Die projizierten Flächen enthalten weiterhin verdeckte Anteile, keine automatische Umwandlung in sichtbare manuelle Eckenumrisse.
- Angeschnittene Quell-/Ausschnittmodule, Auffüllung, überlappende Instanzpixel und ein Sicherheitsrand werden ignoriert. Am Quellbildrand mindestens einen Pixel Kontext verlangen. Die 26 Bilder ohne Annotationen vollständig ignorieren; daraus keine modulfrei bestätigten Negativbilder machen.
- Instanzraster:0Hintergrund, positive lokale Instanznummern,−1Ignorieren. Zusätzliche Semantik:0Hintergrund/1PV/255Ignorieren. Die Schnittstelle liefert separate Instanzmasken **mit Gültigkeitsmaske**. Ein künftiger Trainer muss sie im Verlust/bei Metriken beachten; ignorierte Nullwerte sind keine Negativlabels.

Dies ist eine Adapterprüfung mit einem kleinen Ausschnitt pro Bild, keine vollständige Anlagen- oder Bildabdeckung. Sie ersetzt weder die Prüfung der öffentlichen Beschriftungsqualität noch einen unabhängigen Modellvergleich. Lokale Instanznummern und wiederholte Beobachtungen sind keine bestätigten physischen Modul-IDs.

## Start ohne Installation

Den **vollständigen Block** in PowerShell ausführen:

```powershell
$ErrorActionPreference = 'Stop'
$pvImageCommit = '29b651c229d49d92cceced71e3921ee79564c2fc'
$pvImageStart = Join-Path 'E:\SolarCheck-PVIS-Bildadapter-Start' $pvImageCommit
New-Item -ItemType Directory -Force -Path $pvImageStart | Out-Null
$pvImageZip = Join-Path $pvImageStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvImageCommit" -OutFile $pvImageZip
if ((Get-FileHash -Algorithm SHA256 $pvImageZip).Hash.ToLowerInvariant() -ne '3c8cd2e4234711a511f54a534685b6508d95939efc106c497b8dc404c1b0d6f1') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvImageZip -DestinationPath $pvImageStart -Force
$pvImageSource = Join-Path $pvImageStart "MCM-SolarCheck-$pvImageCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvImageSource 'scripts\MCM_SolarCheck_PVIS_BILDADAPTER.py') --prefix 'E:\SolarCheck-PVIS-Referenz'
```

Während des Laufs erscheint alle zehn Bilder ein Fortschrittszähler. Anschließend folgt ein JSON-Bericht in PowerShell; es öffnet sich zunächst kein Programmfenster. Feste Quelle **29b651c229d49d92cceced71e3921ee79564c2fc**, QuellZIP **3241144 Bytes**, SHA256 **3c8cd2e4234711a511f54a534685b6508d95939efc106c497b8dc404c1b0d6f1**. Alle **694 Python-Dateien** unter src/scripts sowie **9 Konfigurations-/Paketlistendateien** mit dem remote geladenen Archiv bytegleich geprüft; finale HEAD-CI in PR9.

Erwartete Kernwerte:

```json
{
  "check": "solarcheck-pvis-image-adapter-1",
  "status": "adapter_verified_no_training",
  "decoded_images_by_split": {"train": 58, "validation": 142, "test": 0},
  "unannotated_images_ignored_by_split": {"train": 0, "validation": 26, "test": 0},
  "training_validation_image_decoding_verified": true,
  "full_dataset_image_decoding_verified": false,
  "public_preview_images_written": 2,
  "test_pixels_read": false,
  "training_started": false,
  "model_updated": false
}
```

full_dataset_image_decoding_verified=false ist beabsichtigt: Die 84 Prüfbilder bleiben unangetastet. public_preview_images_written=2 bezeichnet nur die beiden öffentlichen Kontrollbilder; es werden kein Trainingsdatensatz und keine Kundenbilder exportiert. Rechteentscheidung bleibt unreviewed, kein Modell im KI-Vergleich auswählen.

## Wiederöffnung und Kontrollbilder

Nach Schließen von PowerShell den folgenden vollständigen Block ausführen. Er prüft den gespeicherten Stand, ohne JPEGs erneut zu dekodieren oder ein Modell zu laden. Bei Erfolg öffnet er die zwei öffentlichen Kontrollbilder im vorhandenen Bildbetrachter:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Bildadapter-Start\29b651c229d49d92cceced71e3921ee79564c2fc\MCM-SolarCheck-29b651c229d49d92cceced71e3921ee79564c2fc\scripts\MCM_SolarCheck_PVIS_BILDADAPTER.py' --prefix 'E:\SolarCheck-PVIS-Referenz' --show
if ($LASTEXITCODE -eq 0) {
    $pvImageReport = Get-Content -LiteralPath 'E:\SolarCheck-PVIS-Referenz\image-adapter.json' -Raw -Encoding UTF8 | ConvertFrom-Json
    $pvImageOutputs = Join-Path 'E:\SolarCheck-PVIS-Referenz\image-adapter' $pvImageReport.adapter_id
    Invoke-Item -LiteralPath (Join-Path $pvImageOutputs 'train-preview.png')
    Invoke-Item -LiteralPath (Join-Path $pvImageOutputs 'validation-preview.png')
} else {
    Write-Host 'Bitte nur den JSON-Diagnoseblock oben mitteilen; keine Neuinstallation.'
}
```

Jedes Kontrollbild zeigt links den nativen RGB-Ausschnitt, mittig die Instanzmaske und rechts ihre Überlagerung. Schwarz ist Hintergrund, Magenta ist ignoriert, andere Farben zeigen lokale Modulinstanzen. Farben sind keine Temperaturwerte oder bestätigten physischen IDs.

Bitte nur kurz prüfen, ob Masken und Modulflächen nachvollziehbar zusammenliegen und angeschnittene Bereiche als ignoriert erkennbar sind. Keine Vollfreigabe aller Module. **Den JSON-Bericht aus --show und einen kurzen Sichtbefund als Text mitteilen**, keine Bilder hochladen. adapter_id, manifest_sha256 und Kennzahlen müssen gegenüber dem ersten Bericht gleich bleiben. Pixel-/Cropzahlen verschiedener Runtime-Versionen dürfen abweichen; innerhalb derselben Quelle und Umgebung muss die Wiederöffnung identisch sein.

## Abbruch, Fortsetzung und Quellschutz

Strg+C bricht ab. Fertige Bildprotokolle bleiben im eigenen versionierten Journal erhalten. Erneuter Start mit demselben Startblock prüft diese Bilder erneut durch Dekodierung und Vergleich; nur fehlende Protokolle werden ergänzt. Unvollständige temporäre Dateien werden nicht als fertige Ergebnisse gelesen. Bereits abgeschlossene gleiche Profilstände werden ohne erneute JPEG-Dekodierung wiederverwendet.

Erst ein vollständiger Lauf veröffentlicht image-adapter.json atomar. Bei Fehler/Abbruch bleiben frühere abgeschlossene Berichte erhalten. Die bestehenden reference.json und training-reference.json sowie Originalarchive ändern sich nicht. Profil, Bibliotheksversionen, Quellcode und Datenpartition sind gebunden. Geänderte Berichte, Protokolle, Kontrollbilder oder Runtime werden beim Wiederöffnen abgelehnt. Ein bewusst neuer Audit erhält einen anderen versionierten Ordner. Die gemeinsame OS-Sperre verhindert parallele Schreibläufe mit den bisherigen PVIS-Befehlen.

Bei Fehler bitte nur den ausgegebenen Diagnoseblock mitteilen. Das vorhandene App-Python auf F: verwenden; keine zusätzliche Installation und keine erneuten Referenzdownloads. Alle Kundendaten, produktive SQLite und bisherigen Modelle bleiben lokal erhalten.

## Nachweise und nächster Entwicklungsschritt

140 gezielte synthetische Tests, davon 24 neue Adapterfälle, bestanden: tatsächliche erzeugte JPEG-Pixel, RGB-/Pixelzuordnung, Mehrfragmente/benachbarte Instanzen, ignorierte Überlappungen/Ränder/Auffüllung, unbekannte Bilder/Gültigkeitsmaske, Testpixelsperre, Abbruch/Fortsetzung/Wiederöffnung, Quellschutz, Manipulation, Parallelprozess und Platzmangel. Die synthetische Kontrolldarstellung ist gesichtet.

Echte öffentliche Linux-Probe:200 JPEGs dekodiert,58/114 geeignete Trainings-/Validierungs-Prüfausschnitte,328/615 Instanzbeobachtungen,26 unannotierte Bilder vollständig ignoriert. Zwei weitere annotierte Validierungs-Prüfausschnitte ohne geeignete vollständige Instanz, keine Negativfreigabe. Wiederöffnungsbericht identisch,0 Testpixelbilder. Diese Werte stammen aus der geprüften Runtime, keine Vollbild-Modulzahlen oder allgemeine Qualitätsquote. Native Windows-CI und reale Windows10-Bedienabnahme werden getrennt dokumentiert; letztere laut Nutzerbericht und beiden Kontrollbildern inzwischen positiv abgeschlossen, keine allgemeine Qualitätsfreigabe.

Als Nächstes einen qualifizierten Trainer verbinden, der Instanzen und Gültigkeit korrekt verarbeitet, mit passenden Daten-/Code-/Modellrechten. Erst danach begrenztes echtes Nachtraining und unabhängige Prüfung. Die öffentliche [PVIS-Datenlizenz](https://zenodo.org/records/23886365/files/LICENSE.md?download=1) nennt CC BY4.0; bei Weitergabe Attribution/Lizenzlink/Änderungskennzeichnung einschließlich Urheberangaben aus dem Zenodo-Zitiervorschlag erhalten. Keine pauschale Produktionsfreigabe oder Weitergabe der Kontrollbilder als eigene Originale.

Keine neue Original-CVUT-Profilfreigabe, keine unveränderten PV-Hawk-Wiederholungen und keine 1000 Pflichtreviews. Thermal bleibt **unvollständig: 280 von 287 Bildern**, mit GeoTIFF-Tags und regulärer Paarimport-Sperre; keine Abdeckungs-/Geometrie-/Celsiusfreigabe.
