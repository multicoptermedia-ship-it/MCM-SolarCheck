# CVUT: öffentlicher PV-Modellpilot unter Windows 10

Stand20.11.2026 · PV-CVUT-INTAKE-01 · [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der Nutzer hat den öffentlichen CVUT-Pilot gewählt. Zuerst ein vorhandenes Modell prüfen und auf demselben zurückgehaltenen lokalen RGB-Ausschnitt vergleichen, anschließend über Nachtraining entscheiden. Wiederholte PV-Hawk-Inferenz trainiert keine Gewichte. Eine bessere Erkennung durch CVUT ist noch nicht belegt.

## RGB-Modellstruktur prüfen – aktueller nächster Schritt20.11.

**Lokale Paketprüfung real bestanden.** Die vorherige Python-Diagnose war TLS_CERTIFICATE; der bewusst durchgeführte Browserdownload mit anschließender lokaler Prüfung funktioniert. Der Quellpfad bleibt privat. Die alten Basis-/Diagnosestarts weiter unten sind Historie, kein Auftrag zum erneuten CVUT-Download.

Beobachtetes öffentliches Archiv: **344288853Bytes**, SHA256 **61d981c2ebdd180f184265fb2429dc4151463721fc9121f805f1b84c8b8ab14b**. Das ist die vom Nutzer erhaltene Version, kein vom Anbieter veröffentlichter Hash. Enthalten sind ausschließlich:

| Datei | Größe | Auswahl |
|---|---:|---|
|UNet_pv_module_rgb.pth|124239509Bytes|RGB-Einzelmodulmodell, für den nächsten Schritt ausgewählt|
|UNet_pv_installation_rgb.pth|124239509Bytes|Gesamtanlage, nicht als Einzelmodulmodell verwenden|
|UNet_pv_module_thermo.pth|124241732Bytes|Thermal, nicht für die RGB-Modulprüfung wählen|

Keine README-/Lizenz-/Architekturdatei im Paket. Die Endung.pth bestätigt weder die konkrete Architektur noch einen kompatiblen Ladeweg. Datenlizenz CC BY4.0 nicht pauschal auf Gewichte/Code/Runtime übertragen. Kein neues Modell wurde geladen/trainiert oder zur Nutzung freigegeben.

Die neue Option **--inspect-rgb-layout** untersucht nur dieses per Größe/SHA gebundene öffentliche ZIP. Sie liest die RGB-Datei in eine automatisch gelöschte temporäre Datei im eigenen E:-Prüfordner, berechnet deren Hash und analysiert begrenzte interne Metadaten mit der Standardbibliothek. Keine Python-/PyTorch-/Pickle-Konstruktoren aus dem Modell ausführen, keine Tensoren/Architektur rekonstruieren, kein Internetzugriff/Installer in diesem Modus. Schichtnamen und syntaktische Formhinweise sind noch kein Nachweis eines passenden Vorwärtslaufs. Original-ZIP und alter Paketbericht bleiben erhalten.

Auf E: mindestens150MiB zusätzlichen freien Platz für die temporäre öffentliche RGB-Datei vorsehen. **Keine neue Software installieren.** In PowerShell diesen vollständigen Block ausführen; beim Pfad denselben bereits heruntergeladenen öffentlichen ZIP wählen:

```powershell
$ErrorActionPreference = 'Stop'
$cvutCommit = 'd09e130793ba5da4244adf61f9542fac1ddefaf0'
$cvutStart = Join-Path 'E:\SolarCheck-CVUT-Start' $cvutCommit
New-Item -ItemType Directory -Force -Path $cvutStart | Out-Null
$cvutScript = Join-Path $cvutStart 'MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py'
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/$cvutCommit/scripts/MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py" -OutFile $cvutScript
if ((Get-FileHash -Algorithm SHA256 $cvutScript).Hash.ToLowerInvariant() -ne '51c6ea11739929492dbc66294ced5e2347358f8e8523abaa0dc9aebaec12c01a') {
    throw 'Skript-Pruefsumme stimmt nicht. Nicht gestartet.'
}
$cvutZip = (Read-Host 'Vollstaendiger Pfad zur bereits heruntergeladenen PV_UNET_models.zip').Trim().Trim('"')
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' $cvutScript --archive $cvutZip --inspect-rgb-layout
if ($LASTEXITCODE -ne 0) { Write-Host 'Bitte nur den Diagnoseblock als Text mitteilen. Keine Neuinstallation erforderlich.' }
```

Feste Skriptquelled09e1307/22178Bytes, SHA25651c6ea11739929492dbc66294ced5e2347358f8e8523abaa0dc9aebaec12c01a, aus GitHub remote bytegleich geprüft. Kein Git-Checkout erforderlich; bestehendes F:-Python, OpenSfM und PV-Hawk-Environment erhalten.

**Danach nur den JSON-Text mit check solarcheck-cvut-rgb-layout-1 mitteilen**, bei Fehlern solarcheck-cvut-failure-1. Keine Bilder/privaten Berichte/Modellgewichte hochladen. Der vollständige neue Bericht liegt in E:\SolarCheck-CVUT-Paketpruefung\cvut-rgb-layout.LOCAL.json. Er enthält öffentliche Parameterbezeichner, beobachtete Gewichtshashes/Format-/Formhinweise und False-Freigaben; keine Bilddaten, privaten Pfade oder bestätigte Modellarchitektur. Der Bericht ist kein aktivierbares Modellmanifest.

39synthetische Paket-/Struktur-/Diagnosetests plus zwei Übergabeprüfungen lokal grün: beobachtetes Archiv erzwingen, nur RGB-Mitglied lesen, Schicht-/Formhinweise, Test-Pickle ohne Konstruktoraufruf, Metadaten-/Pfadgrenzen, Abbruch→Fortsetzung/Wiederöffnung/Tempbereinigung und alte Berichte/Quellbytes erhalten. Reale RGB-Metadaten hier noch nicht verfügbar: eigener Anbieterzugriff weiter HTTP503. Neue exakte HEAD-CI in PR9 belegen; reale Windows10-Strukturprüfung offen. Nach dem Ergebnis erst passende Architektur, Eingabe-/Masken-Nachverarbeitung, Lizenz und Laufzeit qualifizieren, dann bestehenden ROI-/GIS-Vergleich verwenden.

## Aktualisierung nach dem Abbruch20.11.

Die gemeldete PowerShell-Zeile mit `throw` war eine zusätzliche Abbruchmeldung. Die alte Skriptfassung unterdrückte den eigentlichen Fehlergrund. Weil weder HTTP-Code noch Fortschritt mitgeteilt wurden, ist die konkrete Ursache auf dem Nutzerrechner noch offen. Hier liefert der Anbieter weiterhin HTTP503; das beweist nicht denselben Fehler auf Windows10. Keine neue Software installieren und keine Zertifikatsprüfung ausschalten.

Den **aktualisierten vollständigen PowerShell-Block unter „Einmalige Paketprüfung ohne neue Software“** unten einmal ausführen. Vorhandenes F:-Python und eigener E:-Paketordner bleiben erhalten. Der Block lädt nur die korrigierte feste Skriptfassung und startet die gleiche Paketprüfung. Bei einem Fehler erscheint nun ein JSON-Diagnoseblock, ohne zusätzliche PowerShell-throw-Fehlerlawine. Erfolg bleibt eine Paketliste, noch kein KI-Ergebnis.

| error_code | Bedeutung / nächster Schritt |
|---|---|
|HTTP_ERROR|`http_status` nennt die Serverantwort, z.B.503. Offiziellen Download im Browser prüfen; keine Installationswiederholung.|
|TLS_CERTIFICATE / TLS_CONNECTION|Python kann Zertifikat/HTTPS-Verbindung nicht bestätigen. Prüfung aktiv lassen; Diagnosecode mitteilen, offiziellen Browserdownload bewusst prüfen.|
|DNS_LOOKUP / NETWORK_CONNECTION / NETWORK_TIMEOUT|Namensauflösung, Verbindung oder30Sekunden-Zeitlimit betroffen. Code/gegebenenfalls numerische Fehlernummer mitteilen.|
|DOWNLOAD_INTERRUPTED / INVALID_ZIP|Abgebrochene Übertragung oder kein lesbares vollständiges ZIP. Keine Modellausführung; letzter Bericht bleibt.|
|LOCAL_ACCESS / LOCAL_IO / DISK_FULL / LOCAL_FILE_MISSING / LOCAL_METADATA|Dateisperre, Schreib-/Lesezugriff, Platz, fehlende Datei oder unlesbare lokale Steuerdatei. Keine vorhandenen Projektdateien/Ergebnisse vorsorglich löschen.|
|PACKAGE_CHECK|Konkrete feste Begründung wird angezeigt, z.B.unerwartete Downloadantwort oder geändertes Archiv. Bedingung erhalten, keine fremde Quelle freischalten.|
|UNEXPECTED_ERROR|Fehlerklasse wird ohne rohe Fehlermeldung genannt. Diesen Diagnoseblock mitteilen.|

Der Fehlerblock enthält feste Erklärungen, Fehlerklasse und gegebenenfalls numerischen HTTP-/Betriebssystemcode. Er übernimmt keine lokalen Dateipfade, Proxyadressen, Roh-Ausnahmetexte, Bilddaten oder Notizen. Er wird nicht über den letzten erfolgreichen Paketbericht geschrieben. `model_loaded`, `training_started`, `inference_started` und `production_approved` bleiben false.

## Geprüfte Anbieterangaben und offene Punkte

| Quelle | Eignung / Stand |
|---|---|
|[CVUT PVsegmentation](https://imr.ciirc.cvut.cz/Datasets/PVsegmentation)|136RGB-/74Thermalbilder, über3000Masken einzelner Module; Maskenbilder und YOLO-Konturen. Datensatz laut Anbieter **CC BY4.0**, einschließlich kommerzieller Verwendung mit Namensnennung. Keine pauschale Rechtefreigabe sämtlicher separater Modelle/Software.|
|[Öffentliches Downloadverzeichnis](https://imr.ciirc.cvut.cz/uploads/Datasets/)|PV_UNET_models.zip ca.344MB; PV_YOLOv8_models.zip ca.34MB; PV_module_segmentation_dataset.zip ca.700MB. Angaben aus indexierten Primärseiten; hier direkte Zugriffe19.11. HTTP503, tatsächlicher Paketinhalt noch ungeprüft.|
|[Publikation Kozák et al.](https://arxiv.org/abs/2501.14587)|U-Net erzeugt eine semantische Maske; morphologische Verarbeitung und Komponenten liefern Modulrechtecke. YOLOv8 liefert Instanzen. U-Net ist kein direkter Ersatz für das vorhandene ONNX-Instanzprotokoll. Reflexionen und Layoutwechsel verursachen auch dort Ausfälle. Veröffentlichte Erfolgsraten nicht auf unser Orthofoto übertragen.|

**Auswahl:** zuerst das U-Net-Modellpaket inventarisieren. Es enthält laut Anbieter auch ein Modell für ganze PV-Installationen; dieses unterscheidet keine Einzelmodule. Konkretes RGB-Modulmodell, Architektur, Dateiformat, Normalisierung/Größe, Masken-Nachverarbeitung, Gewichts-/Codelizenz und Windows-CPU-Laufzeit erst anhand des Pakets qualifizieren. Keine `.pt`/Pickle-Datei laden und keinen mitgelieferten Code ausführen. Kein automatischer Ultralytics-/AGPL-/Enterprise-Einsatz. Keine erfundene ONNX-Konvertierung oder Umbenennung als kompatibles Modell.

Datensatz-Attribution für eine spätere Nutzung: Viktor Kozák, Karel Košnar, Jan Chudoba, Miroslav Kulich und Libor Přeučil; Czech Technical University in Prague, PVsegmentation, CC BY4.0, Originalquelle und [Lizenz](https://creativecommons.org/licenses/by/4.0/) nennen; Änderungen kennzeichnen und mindestens eine vom Anbieter genannte Publikation zitieren. Erst nach tatsächlicher Datenaufnahme konkrete Version/Dateiprüfsumme/Änderungen ergänzen. Die Daten wurden hier noch nicht heruntergeladen.

## Einmalige Paketprüfung ohne neue Software

Das eigenständige Skript [MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py](../scripts/MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py) verwendet nur vorhandenes Python und dessen Standardbibliothek. Der feste Download ist ausschließlich das öffentliche **U-Net-Modellarchiv**, keine Trainingsbilder. Eigener Ordner `E:\SolarCheck-CVUT-Paketpruefung`, ungefähr400MiB freien Platz vorsehen. F:-Python, OpenSfM, bestehende KI-Umgebung und deren gespeicherte Ergebnisse bleiben erhalten.

In **PowerShell** diesen vollständigen Block ausführen. Er lädt ein einziges festes Skript (13881Bytes), prüft dessen SHA256 und startet die öffentliche Paketprüfung mit dem vorhandenen F:-Python. Kein Git-Checkout und keine neue Python-Umgebung erforderlich.

```powershell
$ErrorActionPreference = 'Stop'
$cvutCommit = '2e730256b249540627854e0bbf06947669b32896'
$cvutStart = Join-Path 'E:\SolarCheck-CVUT-Start' $cvutCommit
New-Item -ItemType Directory -Force -Path $cvutStart | Out-Null
$cvutScript = Join-Path $cvutStart 'MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py'
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/$cvutCommit/scripts/MCM_SolarCheck_CVUT_PAKETPRUEFUNG.py" -OutFile $cvutScript
if ((Get-FileHash -Algorithm SHA256 $cvutScript).Hash.ToLowerInvariant() -ne '93e1b6fe70cef77b88fcd29e2d7a65d350dc51861f6016c3f818e6579e1dc44c') {
    throw 'Skript-Pruefsumme stimmt nicht. Nicht gestartet.'
}
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' $cvutScript
if ($LASTEXITCODE -ne 0) { Write-Host 'Bitte den Diagnoseblock oben ab check als Text mitteilen. Keine Neuinstallation erforderlich.' }
```

Feste Skriptquelle2e730256 wurde aus GitHub geladen und mit dem Repository bytegleich geprüft. SHA256 gilt nur für dieses Startskript, nicht für das noch ungeprüfte CVUT-Modellarchiv. Bei erneutem Start kann derselbe Block verwendet werden.


Das Skript zeigt Downloadfortschritt und anschließend eine öffentliche Dateiliste mit Größe/SHA256. Der Hash dokumentiert die lokal erhaltenen Bytes, **keinen bereits bekannten Anbieterhash**. Vollständiger Bericht `E:\SolarCheck-CVUT-Paketpruefung\cvut-package.LOCAL.json`: Dateiliste und höchstens256KiB README-/Lizenztexte. Keine Modelle extrahieren/deserialisieren, keine Inferenz/Trainingsläufe oder Installationen. Verschlüsselte/verknüpfte/ungewöhnliche ZIP-Einträge und Größenüberschreitungen ablehnen. Der Bericht ist **kein Modellmanifest** für „KI-Modellvergleich starten“.

**Ergebnis mitteilen:** Nur den ausgegebenen JSON-Text mit `check: solarcheck-cvut-package-inspection-1` und öffentlicher Paketliste oder mit `check: solarcheck-cvut-failure-1` und konkretem Fehlercode. Keine Bilder, privaten Pfade, bisherigen KI-Berichte oder Projektdateien nötig. Es wurden noch keine Module deiner Anlage damit analysiert.

**Abbruch/Fortsetzung:** Strg+C entfernt den begonnenen Download. Erneut denselben Start ausführen; ein fertiges Paket wird ohne neuen Download inventarisiert und gegen den gespeicherten lokalen Hash geprüft. Nach hart beendetem Prozess wird ein unvollständiger Download neu begonnen, kein Byte-Resume behauptet. Paralleler Start wird gesperrt; Betriebssystem gibt die Sperre bei Prozessende frei. Ein bestehender Bericht bleibt bei Download-/Paketfehlern oder verändertem Archiv erhalten. Fremde gefüllte Zielordner werden abgelehnt.

**Falls auch lokal HTTP503 erscheint:** keine wiederholten Installationen versuchen. Die Paketprüfung ist dann am Anbieterzugang blockiert, nicht als bestanden markieren. Optional das exakt verlinkte [PV_UNET_models.zip](https://imr.ciirc.cvut.cz/uploads/Datasets/PV_UNET_models.zip) später bewusst im Browser laden und dasselbe Skript mit `--archive 'ABSOLUTER_PFAD_ZU\PV_UNET_models.zip'` ausführen. Nur dieses öffentliche Modellpaket auswählen; Originalarchiv wird nicht verändert/kopiert. Die Prüfung ersetzt keine Veröffentlichung der fehlenden Modelllizenz.

## Danach: bestehende Vergleichskette verwenden

Nach Paket-/Rechte-/Runtime-Prüfung einen konkret gepinnten RGB-Moduladapter mit synthetischer echter Modellprobe vorbereiten. Anschließend bewusst lokal auf demselben gespeicherten Ausschnitt vergleichen: fehlende/zusätzliche/teilweise/doppelte Umrisse, Modulgrenzen, Laufzeit und manuellen Aufwand. Die acht gelben Umrisse sind eine Teilreferenz; weder Vollständigkeitsquote noch allgemeine Genauigkeit daraus ableiten. Neues Ergebnis separat vom PV-Hawk-Ausgang erhalten. Keine automatische Übernahme oder Änderung der gespeicherten Entwürfe.

Falls Nachtraining nötig ist: zuerst öffentliche CVUT-Bilder/Masken in einem getrennten lokalen Datenordner mit Herkunft/Attribution aufnehmen; RGB/Thermal und Gesamtanlagen-/Modulmasken trennen. Labelvollständigkeit, Randfälle, Datenqualität und Gruppen nach Anlage/Flugsequenz prüfen. Keine benachbarten Aufnahmen/gleichen Module zwischen Training und unabhängiger Prüfung verteilen. Kundendaten nicht in diesen öffentlichen Trainingspilot übernehmen. Training nur mit konkret qualifiziertem Trainer und begrenztem Lauf. [Vorhandene Trainingsbausteine](PV_RGB_ORTHOPHOTO_TRAINING_PREPARATION.md) wiederverwenden; Klassifikationstrainer ist kein Instanzsegmentierer.

[PVIS-10K](https://zenodo.org/records/23886365) bleibt spätere Ergänzung: rund31GB, COCO-Instanzpolygone/Standort-Split, keine fertigen überwachten Checkpoints laut [Codequelle](https://github.com/plzhang1998/PVDataset). Keine Massendownloads/SAM3-/Linux-Umgebung jetzt einführen.

## Nachweis und Grenzen

Windows-Prüfung fand eine abweichende ZIP-Namensnormalisierung: Originalnamen werden jetzt vor Normalisierung geprüft und manipulierte Testnamen plattformgleich geschrieben.13synthetische Paketprüfungen lokal bestanden: Download/Wiederverwendung/Wiederöffnung, HTTP503→Fortsetzung, Abbruch/Quellschutz, geänderte Archive, fremde Ordner, Git-/Link-/ZIP-/Größengrenzen und paralleler Start. Die ursprünglichen13Pakettests waren unter Windows3.11/3.12 grün(f27f3919); jetzt insgesamt30synthetische Paket-/Diagnosetests plus zwei Übergabeprüfungen lokal grün. Neue exakte HEAD-CI in PR9 separat belegen. Tatsächlicher CVUT-Download hier HTTP503, deshalb keine reale Format-/Gewichts-/Lizenz-/Inferenzprobe oder Windows10-Abnahme behaupten.

Dauerlabel **unvollständig: 280 von 287 Bildern**, GeoTIFF-Tags, reguläre RGB-/Thermal-Paarimport-Sperre und alle offenen Fachfreigaben erhalten. Kein Matching, keine Rekonstruktion, keine bestätigte vollständige Abdeckung/Geometrie/Celsius/physische Modul-ID. Feature-Branch/DraftPR9, main unverändert.
