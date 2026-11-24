# Öffentliche RGB-Modulreferenz auf Windows 10

Stand 24.11.2026 · PVIS-INTAKE-01 · [aktueller Entwicklungsstand](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der synthetische Trainingsversuch und seine Wiederöffnung sind laut Nutzer erfolgreich. Er hat die Trainingsmechanik geprüft, kein PV-Modell verbessert. Jetzt folgt die begrenzte Aufnahme einer öffentlichen Referenz: **PVIS-10K, Version 1.0.0**, [Zenodo/DOI 10.5281/zenodo.23886365](https://zenodo.org/records/23886365).

Der neue Befehl lädt zwei fest ausgewählte Originalpakete sowie README, Datenlizenz und Anbietermanifest. Er prüft SHA-256, Paketstruktur und COCO-Annotationen und speichert einen wieder lesbaren Bericht. **Er öffnet kein Programmfenster und startet kein Training.** Die Bilder bleiben unverändert in den öffentlichen ZIPs; keine Entpackung, Bilddekodierung, Normalisierung oder Installation. Kundendaten, Projektdateien, bisherige Modelle und SQLite bleiben unberührt.

## Auswahl und fachliche Grenzen

| Anlage | Aufteilung | RGB-Bilder | Modulbeobachtungen | ZIP-Bytes |
|---|---|---:|---:|---:|
| Ningbo 009 | Training | 58 | 16.697 | 201.375.386 |
| Ningbo 024 | unabhängige Prüfanlage | 84 | 20.766 | 251.234.092 |
| Zusammen | zwei getrennte Anlagen | 142 | 37.463 | 452.609.478 |

Beobachtungen zählen wiederholte Ansichten desselben Moduls mit. Die lokalen Annotations-IDs sind keine bestätigten physischen Modul-IDs. Ausschnitte und Ableitungen einer Anlage müssen dauerhaft in deren Datenteil bleiben. **Die Prüfanlage darf nicht zur Modell-, Schwellen- oder Parameterwahl dienen.** Eine zusätzliche getrennte Validierungsanlage fehlt in dieser kleinen Auswahl und muss vor einem echten Trainingsvergleich ergänzt werden.

PVIS enthält ganze Modulpolygone statt Solarzellen oder gesamter Anlagenflächen. Teilweise verdeckte Module behalten laut Anbieter auch ihre verdeckten projizierten Umrissteile. Das unterscheidet sich von unseren geprüften sichtbaren Ecken. Es gibt hier keine automatische Sichtbarkeitsfreigabe; diese Daten dürfen nicht ungeprüft als sichtbare vollständige Umrisse übernommen werden. Mehrere Polygonfragmente bleiben eine Instanz. Keine 3D-Rekonstruktion oder Kameralösung aus diesem Datensatz wird übernommen.

Die [Datenlizenz](https://zenodo.org/records/23886365/files/LICENSE.md?download=1) nennt **CC BY 4.0** für Bilder, COCO-Annotationen und Begleitdokumente. Kommerzielle Nutzung ist unter ihren Bedingungen möglich: Namensnennung, Lizenzlink und Änderungen kennzeichnen, keine Billigung durch Urheber behaupten. Datensatzversion/DOI und Urheberreihenfolge aus dem Zenodo-Zitiervorschlag bei Verwendung übernehmen. Software und Modellgewichte unterliegen eigenen Lizenzen. Der bestehende Rechtevertrag bleibt **unreviewed**, keine technische Pauschalfreigabe für Produktweitergabe oder Kundentraining.

Festwerte aus dem [Anbietermanifest](https://zenodo.org/records/23886365/files/archive_manifest.csv?download=1):

```text
PVDataset_train_009.zip
SHA256 f9b136c5809f37f1d714c402e642876869955598a9a4db8c3d5909a4ffa6b9fa
PVDataset_test_024.zip
SHA256 9db6b88c49936e47c74f1c77af24e95cf9807e0558c5ff799c16be402beee420
```

## Start ohne Installation

Vorhandenes App-Python auf F: verwenden. Der eigene Ordner **E:\SolarCheck-PVIS-Referenz** muss anfangs leer sein oder von genau dieser Paketprüfung stammen. Für die beiden ZIPs und Dokumente reichen mindestens **550 MB freier Platz**; kein 31-GB-Gesamtdatensatz. Der Quellcode-Start wird separat unter E: abgelegt. Bestehende Python-Umgebungen bleiben unverändert.

Den **vollständigen Block** in PowerShell ausführen:

```powershell
$ErrorActionPreference = 'Stop'
$pvReferenceCommit = 'SOURCE_COMMIT'
$pvReferenceStart = Join-Path 'E:\SolarCheck-PVIS-Start' $pvReferenceCommit
New-Item -ItemType Directory -Force -Path $pvReferenceStart | Out-Null
$pvReferenceZip = Join-Path $pvReferenceStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvReferenceCommit" -OutFile $pvReferenceZip
if ((Get-FileHash -Algorithm SHA256 $pvReferenceZip).Hash.ToLowerInvariant() -ne 'SOURCE_SHA256') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvReferenceZip -DestinationPath $pvReferenceStart -Force
$pvReferenceSource = Join-Path $pvReferenceStart "MCM-SolarCheck-$pvReferenceCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvReferenceSource 'scripts\MCM_SolarCheck_PVIS_REFERENZ.py') --prefix 'E:\SolarCheck-PVIS-Referenz'
```

Feste Startquelle **SOURCE_COMMIT**, ZIP **SOURCE_BYTES Bytes**, SHA256 **SOURCE_SHA256**. Vor Übergabe remote gegen alle Python-Dateien unter src/scripts sowie Konfiguration/Paketlisten geprüft. Keine Pakete werden installiert oder ausführbare Fremddateien aus dem Datensatz geladen.

Erwartet: **check=solarcheck-pvis-reference-1**, **status=inventory_verified_not_training_ready**, **images=142**, **annotation_observations=37463**, **publisher_sha256_verified=true**, **station_disjoint=true**. validation_stations bleibt0; training_started, training_authorized, model_updated, customer_images_read und sämtliche Qualitäts-/Produktfreigaben bleibenfalse. Kein neues Modellmanifest für den KI-Vergleich auswählen.

## Wiederöffnung und Abbruch

Nach dem Schließen von PowerShell lässt sich der gespeicherte Stand ausschließlich lokal nachprüfen:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Start\SOURCE_COMMIT\MCM-SolarCheck-SOURCE_COMMIT\scripts\MCM_SolarCheck_PVIS_REFERENZ.py' --prefix 'E:\SolarCheck-PVIS-Referenz' --show
```

**--show** prüft ZIP-/Dokumentprüfsummen und Annotationen erneut gegen den gespeicherten Bericht. Kein Netzabruf, kein Modellstart. Die Kennzahlen bleiben gleich. Bitte nur diesen JSON-Bericht als Text mitteilen; keine Bilder oder privaten Berichte senden.

Abbruch mit Strg+C entfernt die laufende unvollständige Kopie. Ein weiterer Start ohne --show verwendet vollständig heruntergeladene und erneut SHA-geprüfte Dateien; nur die unterbrochene Datei beginnt von vorn. Es gibt keine behauptete Fortsetzung mitten im Datenstrom. Nach hartem Beenden wird eine eigene .download-Datei beim erneuten Start ersetzt; nie als gültiges Archiv gelesen. Ein vorher vollständig gespeicherter Bericht bleibt bei Fehler/Abbruch erhalten. Veränderte Archive/Berichte werden abgelehnt, nicht still repariert. Die Prozesssperre verhindert parallele Paketprüfungen und wird vom Betriebssystem beim Prozessende freigegeben.

## Falls Python erneut TLS_CERTIFICATE meldet

Zertifikatsprüfung eingeschaltet lassen. Über den Browser diese fünf offiziellen Dateien in **einen eigenen Quellordner** laden; Namen unverändert lassen:

- [PVDataset_train_009.zip](https://zenodo.org/records/23886365/files/PVDataset_train_009.zip?download=1)
- [PVDataset_test_024.zip](https://zenodo.org/records/23886365/files/PVDataset_test_024.zip?download=1)
- [LICENSE.md](https://zenodo.org/records/23886365/files/LICENSE.md?download=1)
- [README.md](https://zenodo.org/records/23886365/files/README.md?download=1)
- [archive_manifest.csv](https://zenodo.org/records/23886365/files/archive_manifest.csv?download=1)

Dann den bereits geladenen SolarCheck-Prüfer mit dem tatsächlichen Quellordner starten. Das Beispiel fragt ihn interaktiv ab, ohne Pfad in Diagnoseberichte zu übernehmen:

```powershell
$pvPublicSource = Read-Host 'Vollstaendiger Pfad zum Ordner mit den fuenf oeffentlichen PVIS-Dateien'
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Start\SOURCE_COMMIT\MCM-SolarCheck-SOURCE_COMMIT\scripts\MCM_SolarCheck_PVIS_REFERENZ.py' --prefix 'E:\SolarCheck-PVIS-Referenz' --archive-dir $pvPublicSource
```

Dieser Weg kopiert ausschließlich die fünf fest gebundenen öffentlichen Dateien in den Referenzordner, lässt die Downloads unverändert und verwendet keine Netzverbindung. Bei Fehler bitte nur den ausgegebenen Diagnoseblock mitteilen; keine Neuinstallation erforderlich.

## Prüfbelege

92gezielte synthetische Tests bestanden (Paket-/COCO-Verträge, Quellen-/Berichtsschutz, Abbruch/Neustart/Wiederöffnung, paralleler Prozess, TLS/Platzmangel). Zusätzlich beide offiziellen ZIPs auf Linux anhand der Anbieter-SHA geprüft und ihre COCO-Daten inventarisiert:142Bilder/37463Beobachtungen, in beiden Anlagen keine unannotierten Bilder und keine Mehrfragmentinstanzen. Der vollständige lokale Kopier-/Prüfweg und --show lieferten denselben Bericht. Keine Bildpixel dekodiert. Native Windows-CI und echte Windows10-Bedienabnahme werden getrennt dokumentiert; finale CI-Belege in PR9.

## Weiterer Entwicklungsschritt

Nach lokaler Paket-/Wiederöffnungsabnahme: Sichtbarkeits-/Beschriftungsregeln qualifizieren, unabhängige Validierungsanlage ergänzen und den bestehenden Trainings-/Prüfadapter mit passenden Rechten verbinden. Erst dann begrenztes reales Nachtraining und unabhängiger Modellvergleich. Die ungeklärte CVUT-Originalvorverarbeitung wird durch diesen Import nicht bestätigt. Keine weitere unveränderte PV-Hawk-Erkennung als Lernfortschritt ausgeben. Thermal bleibt **unvollständig: 280 von 287 Bildern**, einschließlich Metadaten und Paarimport-Sperre; keine Abdeckungs-, Geometrie- oder Celsiusfreigabe.
