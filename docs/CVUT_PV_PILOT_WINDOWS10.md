# CVUT: öffentlicher PV-Modellpilot unter Windows 10

**Fortsetzung21.11.:** Lernvorbereitung laut Nutzer gespeichert/wiedergeöffnet;29Einträge, teilweise Ecken nicht sichtbar. Vor Training zuerst [unklare Bereiche ausnehmen und Lernmaske prüfen](PV_RGB_ORTHOPHOTO_TRAINING_PREPARATION.md). Kein neuer Modell-/Setup-Lauf, Originalprofil weiter ungeklärt; keine bestätigte Qualitätsverbesserung.

Stand20.11.2026 · PV-CVUT-INTAKE-01 · [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Der Nutzer hat den öffentlichen CVUT-Pilot gewählt. Zuerst ein vorhandenes Modell prüfen und auf demselben zurückgehaltenen lokalen RGB-Ausschnitt vergleichen, anschließend über Nachtraining entscheiden. Wiederholte PV-Hawk-Inferenz trainiert keine Gewichte. Eine bessere Erkennung durch CVUT ist noch nicht belegt.

## Aktueller Feldbefund20.11.: technisch erfolgreich, Erkennung nicht bestanden

**CVUT-FIELD-QUALITY-01:** Der Nutzer hat den gespeicherten RGB-Ausschnitt mit dem Kandidaten tatsächlich verglichen. Kennzahlen: input_profile=cvut-rgb-unit-480x270-candidate-1,73Kandidaten. Die mitgeteilte Ergebnisanzeige meldet acht gespeicherte passende Teilreferenzen, davon keine wiedergefunden, acht nicht wiedergefunden und73zusätzliche ungeprüfte Kandidaten. Sichtbar sind viele kleine Flächen innerhalb ganzer Module und Teilumrisse. Das Ergebnis reicht für automatische Modulgrenzen nicht aus.73ist keine bestätigte Modulzahl; aus acht Teilreferenzen folgen weder eine Gesamtanlagen-Trefferquote noch73nachgewiesene Fehlalarme. Alle Fachflags bleiben false. Dauer und reale Wiederöffnung dieses Berichts noch nicht mitgeteilt.

**diagnostics=null ist hier kein Modellfehler.** Der CVUT-Adapter stellt bisher keine Zwischenzähler bereit; der gemeinsame Bericht erlaubt deshalb null. Die73fertigen Umrisse und die geöffnete Ergebnisansicht belegen den ausgeführten Vergleich. Das ist vom früheren schwarzen technischen Testbild zu unterscheiden.

**Keinen unveränderten Test wiederholen oder neu installieren.** Vorhandene Berichte/Entwürfe/Quelle27ccb184 und beide Pilotumgebungen erhalten. Kein weiteres Matching, Orthofoto, Training oder manuelles Abarbeiten aller73Vorschläge. Es gibt noch keine belegte Korrektur der Ursache.

### Nächster Entwicklungsblock: Originalprofil und öffentliche Referenzprüfung

Die Codeprüfung zeigt den vorhandenen Weg Raster-RGB→BGR→RGB0..1,480×270 und Zwei-Klassen-Softmax/Kanal1 vor Opening3×3/Komponentenrechtecken und bestehenden ROI-/GIS-Filtern. Ein einfacher fehlender RGB-Tausch oder eine einkanalige Sigmoidbehandlung ist in diesem Codeweg nicht gefunden. Das beweist nicht die originale CVUT-Vorverarbeitung oder Klassenzuordnung.

Die [Publikation, Abschnitte3.3.1/4.1.3](https://arxiv.org/html/2501.14587v1) nennt480×270, Schwelle0,8, Erosion/Dilatation und Komponentenrechtecke. Exakte Normalisierung, Kanalzuordnung und Kernel sind daraus nicht vollständig belegt. Die [Anbieterseite](https://imr.ciirc.cvut.cz/Datasets/PVsegmentation) beschreibt öffentliche RGB-Bilder samt Modulmasken; direkter Abruf hier20.11. Timeout/502. Keine Gewichte, Bilder oder Pakete in diesem Prüfschritt heruntergeladen. Mögliche Ursachen sind Verarbeitung/Klassenzuordnung, Bildmaßstab, Nachverarbeitung oder mangelnde Übertragbarkeit; keine davon ist aus den jetzigen Zählern bewiesen.

Vor dem nächsten Kundenlauf einen kleinen öffentlichen, annotierten Referenzfall mit nachgewiesener Datenherkunft/Lizenz und zum Gewicht gehörigem Eingabe-/Klassenprofil qualifizieren. Rohmaske und daraus gebildete ganze Modulflächen getrennt gegen die vollständige Referenz prüfen, Profil/Hashes festhalten; keine Auswahl nur nach erwarteter Modulzahl. Wenn die Integration dort nachvollziehbar arbeitet, denselben lokalen Ausschnitt erneut begrenzt vergleichen. Erst danach über geeignetes Nachtraining mit öffentlichen Daten entscheiden. Noch kein Benchmark/Trainer implementiert und keine Modellverbesserung behauptet. Kundenbilder bleiben lokal, keine pauschale Produktions-/Weitergabefreigabe.

## Gespeicherten Ausschnitt vergleichen – bereits ausgeführter Bedienweg20.11.

**Einrichtung und technische CPU-Probe auf dem Nutzerrechner erfolgreich.** Mitgeteiltes Protokoll solarcheck-cvut-cpu-probe-1: status passed, pretrained_weights_loaded=true,118Zustandseinträge,2Ausgangsklassen, PyTorch2.15.0+cpu, erwarteter Gewichts-SHA8e862b64…fa1cac8/Referenz21d7850f. foreground_pixels_at_080=0 bezieht sich ausschließlich auf das schwarze synthetische Bild. Keine Aussage über erkannte Module der Anlage, Genauigkeit, Abdeckung, Geometrie oder Celsius. Eingabe-/Klassenzuordnungs-/Produktionsflags weiterhin false; kein Training.

**Kein erneuter Setup-/Download-/Installationslauf nötig.** Die alten setuptools65.5-Metadatenwarnungen haben den gezeigten erfolgreichen Ablauf nicht gestoppt; kein vorsorgliches Löschen/Bereinigen von Paketen oder anderen Umgebungen. Ein vollständig unproblematischer pip-check wird daraus nicht behauptet.

1. In der bereits geöffneten Oberfläche vorhandenen Thermal-Lauf13.11./18:58:37/oh9ptgy5 → gespeicherten RGB-Vergleich → gespeicherte PV-Modul-Entwürfe öffnen. Falls geschlossen, nur den unten dokumentierten Oberflächenstart ohne Setup verwenden.
2. Denselben gespeicherten Ausschnitt unverändert verwenden. **KI-Modellvergleich starten(lokal)** → **E:\SolarCheck-CVUT-KI-Pilot\cvut-rgb.LOCAL.json**. Nicht Paket-/Probeberichte oder.pth wählen.
3. Nur den Text aus **KI-Kennzahlen kopieren(ohne Bilder und Pfade)** mitteilen; dazu kurz ganze/passende, fehlende/zu kleine/doppelte Umrisse und Dauer beschreiben. Keine Bilder oder privaten Berichte nötig. Acht gelbe Referenzen sind keine vollständige Anlagenannotation.
4. Schließen → **Gespeicherten KI-Vergleich öffnen** → **CVUT-Kandidat**; bei zwei Berichten bleibt **Bisheriger KI-Vergleich** separat verfügbar. Ohne erneute Inferenz wiederöffnen. Ergebnisse/Entwürfe/Originale erhalten.

Dieser erste reale Ausschnittvergleich ist ausgeführt; sein Feldbefund steht oben. Eine erfolgreiche Wiederöffnung des CVUT-Berichts ist noch nicht mitgeteilt. Die bestandene schwarze Modellprobe ist ein technischer Lade-/Laufzeitnachweis, keine fachliche Erkennungsfreigabe. Keine neuen Matching-/Orthofoto-/Trainingsläufe. Dauerlabel unvollständig280/287/GeoTIFF-Tags/Paarimport-Sperre und alle False-Fachflags bleiben.

## CPU-Pilot einrichten – real technisch bestanden20.11.

**Die Strukturprüfung ist real bestanden.** Öffentliches RGB-Modell124239509Bytes, SHA256 **8e862b6498f8501d5042a9f0127c6dfde1c75f0b22c51d6db56b127a9fa1cac8**; moderner PyTorch-ZIP-Container/Pickleprotokoll2 mit118Schichtbezeichnern/-formhinweisen und ausschließlich den beobachteten Standardreferenzen collections.OrderedDict, torch.FloatStorage/LongStorage und torch._utils._rebuild_tensor_v2. Drei RGB-Eingänge, transponierte Faltungen und **zwei Ausgänge [2,64,1,1]**. Eine einkanalige Sigmoidbehandlung wäre falsch. Die vorherigen Paket-/Strukturstarts unten sind abgeschlossen und müssen nicht wiederholt werden.

Die Schichtformen passen vollständig zu einer bekannten [U-Net-Referenz](https://github.com/milesial/Pytorch-UNet/tree/21d7850f2af30a9695bbeea75f3136aa538cfc4a/unet), Commit21d7850f2af30a9695bbeea75f3136aa538cfc4a. Deren [GPL-3.0-Lizenz](https://github.com/milesial/Pytorch-UNet/blob/21d7850f2af30a9695bbeea75f3136aa538cfc4a/LICENSE) wird mit den drei kleinen Originaldateien separat im lokalen Pilotordner erhalten; nichts davon wird als permissiv lizenzierter SolarCheck-Code ausgegeben. Das ist ein begrenzter lokaler Kandidat, **keine** Klärung von Produkt-/Weitergaberechten oder aller Drittkomponenten. CVUT-Gewichtsrechte sind separat offen; Dataset-CC-BY4.0 nicht pauschal übertragen. Keine Ultralytics-/AGPL-/Enterprise-Integration.

**Dieses Mal ist zusätzliche Software nötig:** eigene Umgebung **E:\SolarCheck-CVUT-KI-Pilot**, vorhandenes F:-App-Python3.11/3.12-x64 nur als Basis. **PyTorch2.15.0 CPU**, NumPy/OpenCV/rasterio/pyproj/Pillow in dieser eigenen Umgebung, eigene Cache-/Tempordner. Mindestens5GiB freien Platz auf E: vorsehen. Kein TorchVision, CUDA, GPU-/Compiler-/SDK-Setup; kein Paket in F:-Python, OpenSfM oder PV-Hawk installieren. [Offizieller CPU-Wheelkanal](https://download.pytorch.org/whl/cpu/torch/) und [Paketmetadaten2.15.0](https://pypi.org/project/torch/2.15.0/). Das Setup bleibt ein ausdrücklicher manueller Schritt.

Der begrenzte Kandidat prüft das vorhandene öffentliche ZIP und kopiert ausschließlich die RGB-Gewichte in den eigenen Pilotordner. Gewichte per SHA prüfen und ausschließlich mit [torch.load(weights_only=True,map_location=cpu)](https://docs.pytorch.org/docs/stable/generated/torch.load) lesen. Alle118Tensor-Keys/Formen/Datentypen/endlichen Werte prüfen, strict=True, keine benutzerdefinierten Pickle-Globals oder unsichere Fallbackladung. Referenzcode vor Ausführung vollständig gegen SHA prüfen. Erst nach erfolgreichem echtem CPU-Laden und schwarzer synthetischer RGB-Probe entsteht cvut-rgb.LOCAL.json. Alte gültige Manifest-/Probeberichte bleiben bei Fehlern erhalten.

**Kandidatenprofil, nicht als Original-CVUT-Profil bestätigt:** BGR→RGB0..1,480×270Pixel, zwei Klassen via Softmax, Kanal1 als vorläufiger Modulkanal, Pixelgrenze0,8, Opening3×3 und Komponentenrechtecke. Auf native Pixelzentren zurückführen, danach bestehende RGB-/NoData-/Geometrie-/GIS-/Thermalprüfung. Die [CVUT-Publikation](https://arxiv.org/abs/2501.14587) nennt480×270/0,8 und Erosion/Dilatation; sie belegt weder den konkreten Normalisierungscode noch unsere Klassenzuordnung oder Kernelgröße. Deshalb preprocessing_verified/class_mapping_verified=false und sichtbarer Kandidatenhinweis. Referenz-ABI-Kompatibilität ist keine Bestätigung des ursprünglichen Trainings-/Vorwärtscodes oder verbesserter Feldqualität. Ein fester begrenzter Vergleich, keine blinde Parameterrunde.

### Einmaliger PowerShell-Start

Den gesamten Block ausführen. Er lädt eine feste QuellZIP, prüft deren Hash, richtet ausschließlich den neuen Pilotordner ein und rechnet eine synthetische Probe. Bei der Pfadabfrage dasselbe bereits geladene öffentliche PV_UNET_models.zip wählen. **Kein erneuter CVUT-Modelldownload.** Nach erfolgreichem Setup öffnet sich die aktualisierte bisherige Thermal-Oberfläche, noch ohne Anlagen-KI-Lauf.

```powershell
$ErrorActionPreference = 'Stop'
$cvutCommit = '27ccb184b8003bbd3db43d9f55acb661275dfc6d'
$cvutStart = Join-Path 'E:\SolarCheck-CVUT-Start' $cvutCommit
New-Item -ItemType Directory -Force -Path $cvutStart | Out-Null
$cvutSourceZip = Join-Path $cvutStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$cvutCommit" -OutFile $cvutSourceZip
if ((Get-FileHash -Algorithm SHA256 $cvutSourceZip).Hash.ToLowerInvariant() -ne 'e5f41162464497d60074c4fa8515b38b464559a755c53256b083a428aeabdf79') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $cvutSourceZip -DestinationPath $cvutStart -Force
$cvutSource = Join-Path $cvutStart "MCM-SolarCheck-$cvutCommit"
$cvutInput = (Read-Host 'Vollstaendiger Pfad zum vorhandenen oeffentlichen PV_UNET_models.zip').Trim().Trim('"')
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $cvutSource 'scripts\MCM_SolarCheck_CVUT_CPU_PILOT.py') --archive $cvutInput
if ($LASTEXITCODE -eq 0) {
    & 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $cvutSource 'scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py')
} else {
    Write-Host 'CPU-Pilot nicht fertig. Bitte nur Diagnoseblock mitteilen; bestehende Umgebungen erhalten.'
}
```

Feste Quelle27ccb184/ZIP3123544Bytes/SHA256e5f41162464497d60074c4fa8515b38b464559a755c53256b083a428aeabdf79;686Python-Dateien unter src/scripts sowie CVUT-Konfiguration und Paketliste mit Repository bytegleich geprüft. Kein Git-Checkout vorausgesetzt.

Setup hat fünf sichtbare Phasen. **Erst bei check solarcheck-cvut-cpu-probe-1 / status passed weitergehen.** Dieser Bericht enthält einen schwarzen synthetischen Test, keine Anlagenanalyse/Genauigkeit oder Abdeckung. Strg+C beendet Einrichtung/Probe; erneuter Start verwendet geprüfte Gewichte/Quellen und die eigene Umgebung. Ein gefüllter fremder Zielordner wird abgelehnt. TLS-Prüfung bleibt aktiv; Quellenfehler nicht durch Zertifikatsabschaltung beheben. Bitte bei Fehlern nur den festen Diagnoseblock mitteilen, keine kompletten privaten Konsolen-/Projektlogs.

### Danach genau ein vorhandener Ausschnittvergleich

1. Vorhandenen Thermal-Lauf13.11./18:58:37/oh9ptgy5 → gespeicherten RGB-Vergleich → gespeicherte PV-Modul-Entwürfe öffnen. Keine Orthofotos/Rekonstruktion neu starten.
2. Denselben unveränderten gespeicherten Ausschnitt verwenden, damit der PV-Hawk-Ausgang erhalten/vergleichbar bleibt. **KI-Modellvergleich starten(lokal)** → **E:\SolarCheck-CVUT-KI-Pilot\cvut-rgb.LOCAL.json** wählen. Nicht die.pth-Datei oder Paket-/Strukturberichte wählen. Eigener CPU-Worker maximal5Minuten, derselbe Knopf bricht ab.
3. Ergebnis gelb/gespeicherte Teilreferenz, grün/Kandidaten und ausdrücklicher Kandidatenhinweis. **Keine** fachliche Freigabe von Klassen-/Eingabeprofil, Gesamtpark oder Temperatur aus grünen Umrissen. Lokaler Bericht jetzt separat **pv-cvut-model-comparison.LOCAL.json**; bisheriger PV-Hawk-/ONNX-Bericht **pv-model-comparison.LOCAL.json** erhalten.
4. Schließen → **Gespeicherten KI-Vergleich öffnen**. Sind beide vorhanden, zwischen **Bisheriger KI-Vergleich** und **CVUT-Kandidat** wählen. Kein Modellimport/keine neue Inferenz beim Wiederöffnen. Fehler/Abbruch/Timeout erhalten die letzten Ergebnisse und Entwürfe.
5. Nur **KI-Kennzahlen kopieren(ohne Bilder und Pfade)** als Text mitteilen sowie grob passende/fehlende/zu kleine/doppelte Modulvorschläge und Dauer beschreiben. Acht Teilreferenzen keine vollständige Gesamtflächenannotation; zusätzliche Kandidaten nicht automatisch Fehler. Noch kein Kundentraining/1000Pflichtreview.

**Später nur Oberfläche öffnen, ohne Setup/Downloads:**

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-CVUT-Start\27ccb184b8003bbd3db43d9f55acb661275dfc6d\MCM-SolarCheck-27ccb184b8003bbd3db43d9f55acb661275dfc6d\scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py'
```

132gezielte Regressionen und7CVUT-Gates(überlappend) lokal grün, dazu9isolierte Tests mit echter PyTorch2.15.0-CPU-Laufzeit/externem gehashtem Referenzcode und synthetischen Gewichten: alle118Formen, Vorwärtslauf[1,2,270,480], zwei Klassen/Softmax statt Sigmoid, RGB-Reihenfolge, striktes Gewichtsformat, NaN/Shape-/Typfehler, unbekanntes Pickle-Objekt ohne Ausführung, synthetischer Probebericht. Neuer Windows2022-CPU-Job und exakte finale CI in PR9 prüfen. Reale veröffentlichte CVUT-Gewichte hier nicht ausgeführt; Nutzer meldet technische CPU-Probe auf Windows10 bestanden, erster Anlagen-Ausschnittvergleich/Feldqualität weiter offen. Quellen/GeoTIFF-Tags/unvollständig280/287/Paarimport-Sperre/alle Fachflags false erhalten.

## RGB-Modellstruktur prüfen – bereits real bestanden20.11.

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
