# Öffentliche Solarmodul-Wärmebilder für erste lokale SolarCheck-Versuche

## Ergebnis der erneuten Quellen- und Lizenzprüfung (21. Oktober 2026)

**Erste Auswahl:** [Raptor Maps / InfraredSolarModules](https://github.com/RaptorMaps/InfraredSolarModules).
Der Herausgeber stellt ein Archiv mit ca. 20.000 beschrifteten Infrarotbildern bereit.
Die Bildgröße beträgt lediglich **24 × 40 Pixel**, gespeichert als einfache
8-Bit-JPEG-Aufnahmen, **keine radiometrischen DJI-Mavic-3T-Rohmessungen**.
Die zwölf veröffentlichten Klassen heißen:

`Cell`, `Cell-Multi`, `Cracking`, `Hot-Spot`,
`Hot-Spot-Multi`, `Shadowing`, `Diode`, `Diode-Multi`,
`Vegetation`, `Soiling`, `Offline-Module`, `No-Anomaly`.

**Wichtig:** Die vom Herausgeber im README veröffentlichten Klassenhäufigkeiten
summieren sich rechnerisch auf **20.006**, obwohl die Quelle von **20.000**
Bildern spricht. Der lokale Import überprüft daher die im **tatsächlich
vorliegenden Originalarchiv** enthaltenen Labels und berichtet die dortigen
Zahlen. Es wird nicht behauptet, die veröffentlichten Häufigkeiten seien
ein fehlerfreier Goldstandard. Die Klassen werden **nicht** ohne fachliche
Prüfung auf die vorhandenen SolarCheck-/IEC-Fehlerklassifikationen abgebildet.

**Lizenz:** Das offizielle Repository (einschließlich Archiv im
Repo) ist mit **MIT** gekennzeichnet. Originaltext:
`docs/licenses/RAPTOR_MAPS_MIT.txt` (Copyright Raptor Maps, Inc. 2020).
Quelle: [MIT-Lizenz](https://github.com/RaptorMaps/InfraredSolarModules/blob/88e2d1febbcefe401c17ec80b8973f36a02a1653/LICENSE).
MIT verlangt Erhalt des Lizenz-/Copyright-Hinweises. Die Repositorylizenz
ist eine günstige Ausgangslage; die Herkunft und Rechte am Bildmaterial,
eventuell zusätzliche Rechte und die konkret geplante kommerzielle Nutzung
müssen vor Produktfreigabe eigenständig geprüft und dokumentiert werden.
Ein lokaler Referenzeintrag allein ist kein amtliches Rechtsgutachten.

**NICHT aufgenommen:**
[ELPV / ZAE Bayern](https://github.com/zae-bayern/elpv-dataset)
enthält Elektrolumineszenzbilder (keine Infrarot-Flugbilder).
Die eigentlichen Bilder stehen unter **CC BY-NC-SA 4.0** und
dürfen ohne zusätzliche Zustimmung nicht für unsere kommerzielle
SolarCheck-Version verwendet werden. Auch andere freie Forschungsdatensätze
werden ohne klare Bildrechte nicht automatisch zugelassen.

## Unveränderlich referenzierter Originalstand

| Nachweis | Wert |
|---|---|
| Offizieller Herausgeber | Raptor Maps |
| Repository | https://github.com/RaptorMaps/InfraredSolarModules |
| Commit | `88e2d1febbcefe401c17ec80b8973f36a02a1653` |
| Originaldatei | `2020-02-14_InfraredSolarModules.zip` |
| Größe laut Git-Objekt | `15.495.990 Bytes` |
| Git-Blob-SHA1 | `2697c73ef1aa58af4dc8aad35ca182ce2586861a` |
| Lizenz | MIT, Original-LICENSE im selben Repository |
| Verwendung | Offline-Import in eigenen **Forschungsordner**, keine Produktionsfreigabe |

Git-Blob-SHA1 wird über den Git-Objektvorspann
`blob <Dateigröße>\0` plus die originalen Archivbytes berechnet,
also nicht als gewöhnlicher ZIP-Datei-SHA1. Der Import erzeugt
**zusätzlich einen lokalen SHA-256** des verifizierten gesamten ZIP
sowie einen SHA-256 jedes einzelnen Bildes. Die Git-Dateiidentität
ist keine digitale Quellsignatur gegen einen vollständig
kompromittierten Herausgeber oder Angriffe auf SHA1. Es wurde **kein
öffentliches unabhängiges SHA-256-Attest** vorgefunden.

## Schritt 1: Auf einem separaten Windows-Rechner herunterladen

Nur auf einem mit dem Internet verbundenen Vorbereitungsrechner
das Quellrepository bereitstellen und in PowerShell aufrufen:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\prepare_public_infrared_archive.ps1 -DestinationDirectory "C:\SolarCheck-IR-Download"
```

Dieses einzige optionale Skript verwendet einen
`Invoke-WebRequest`-Download von der **festgelegten Commit-Adresse**.
Danach das unveränderte ZIP mit einem vertrauenswürdigen USB-Datenträger
zum Windows-10-Auswertungsrechner übertragen. **Der Offline-Desktop
lädt selbst keine externen Datensätze herunter.** Es wird keine
ZIP-Datei und kein Bildmaterial in den GitHub-Quellcode-Zweig
kopiert.

## Schritt 2: Auf Windows 10 rein lokal importieren

Auf dem Offline-Rechner im Repository `PYTHONPATH=src` setzen
und **einen neuen, bislang nicht vorhandenen** Importordner angeben:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.public_infrared_import --archive "D:\SolarCheck-IR-Download\2020-02-14_InfraredSolarModules.zip" --destination "D:\SolarCheck-Forschung\Raptor-Infrared" --reviewer "Fachliche-Prueferkennung" --license-evidence "MIT-LICENSE-RaptorMaps-2020-und-Pruefakte" --exploratory-only
```

Die manuelle **Lizenz-/Rechteprüfreferenz** ist erforderlich;
das Häkchen ist ausdrücklich **nur Forschungsfreigabe** und ersetzt
keine fundierte Rechte- oder Datenschutzprüfung. Der Import verifiziert
**vor dem Schreiben** den exakten Git-Blob-Inhalt, die ZIP-Pfade,
Metadaten-/Bildzahl-/Größenlimits, die zulässigen zwölf Klassen,
die Vollständigkeit aller Bilddateien, sichere JPG-Dimensionen
und ZIP-Symlinks. Ein neuer Zielordner wird exklusiv angelegt;
ein unvollständiger Import wird wieder gelöscht. Der Import schreibt
`public-infrared-index.json` mit Hashes, Labels und Herkunft sowie
separate Bildkopien nur in das neue lokale Forschungsziel.

**Keine** Änderung an Kundenprojektdaten, Berichtfreigabe,
Kunden-Zustimmungsledger, SolarCheck-Diagnoseklassen oder
produktiven Modellgewichten.

## Schritt 3: Erste experimentelle Auswertung vor Ort

Das folgende **optionale** Baseline-Verfahren benötigt nur die
ohnehin installierte Bibliothek Pillow, **kein** vortrainiertes Modell,
keine PyTorch-Installation und **keine** Internetverbindung:

```powershell
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.public_infrared_baseline --catalog "D:\SolarCheck-Forschung\Raptor-Infrared\public-infrared-index.json" --results "D:\SolarCheck-Forschung\erste-baseline.json" --acknowledge-no-site-groups
```

Die einfache überwachte Näherung lernt aus den
Labeln der Trainingsbilder je Klasse einen Graustufen-Pixelmittelwert
(*nearest centroid*). Die übrigen Bilder dienen als separater
Validierungs-/Testbestand. Es entstehen ausschließlich lokale
Versuchsmetriken (Anzahl, Klassen, Verwechslungen, Trefferquoten).
**Kein** PyTorch-Modell, keine KI-Diagnose für Kundenberichte,
keine Modellfreigabe, keine Modifikation der echten Anlagenprojekte.

**Zentrale methodische Grenze:** Raptor Maps gibt in diesem Archiv
keine zuverlässig belegten ursprünglichen Anlagen-/Modulgruppen
an. Deshalb kann der Baseline-Versuch nur anhand der **Bild-ID**
in 70/15/15-Prozent-Splits aufteilen. **Ähnliche Aufnahmen derselben
Anlage könnten in verschiedenen Splits liegen!** Damit ist die
Testtrefferquote keine unabhängige Leistungsbewertung für echte
PV-Anlagen, keine Aussage zur DJI-Mavic-3T-Übertragbarkeit und
kein fachlicher Nachweis für Thermografie-/IEC-Anforderungen.
Für produktive KI braucht es zusätzlich gruppengetrennte
Anlagendaten, radiometrische Validierung, menschliche Labels,
Fehlerkostenbewertung und eine eigenständige Modellfreigabe.

## Was tatsächlich eingecheckt ist – und was nicht

Eingecheckt sind Quellreferenz mit Archiv-Commit/Blob-Identität,
die lokale sichere Importfunktion, der unveränderliche
Forschungsstatus, die lokale Baseline, synthetische ZIP-/Bildtests,
Downloadanleitung und der verpflichtende MIT-Hinweis.

**Nicht eingecheckt oder hier ausgeführt:** 15,5 MB Original-ZIP,
20.000 Originalbilder, echte externe Download-/Importausführung,
Windows-10-Hardwarevalidierung sowie echter PyTorch-Lauf mit den
fremden Bildern. Die originalen Daten müssen explizit auf dem
verbundenen Vorbereitungsrechner bezogen und separat auf dem
Offline-Rechner importiert werden. Der getrennte TorchVision-Trainer
wird **nicht** automatisch mit diesen noch nicht
anlagengruppierten Bilddaten verbunden.
