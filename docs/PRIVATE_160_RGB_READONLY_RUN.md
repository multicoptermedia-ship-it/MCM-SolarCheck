# Privater 160-RGB-Gesamtflug: Windows-10-Read-only-Lauf

**Stand: 29.10.2026 – Entwicklungskandidat auf Draft PR #9.** Status und Sicherheitsgrenzen: [AKTUELLER_ENTWICKLUNGSSTAND.md](AKTUELLER_ENTWICKLUNGSSTAND.md).

## Zweck und Ausgangslage

Ein zusammenhängender **vollständiger** Flug aus sechs DJI-RGB-Archiven
(`*.zip` sowie ein tatsächlich ZIP-kodiertes `*.tip`) soll direkt aus
privaten Original-JPEGs rekonstruiert werden. Es gibt **kein** neues
Archiv-Inventurprojekt, kein erneutes 2D-Seam-Experiment und keinen
SQLite-Import. Bereits bekannte 160 Bilder (0001–0160) werden **im Rahmen
des geplanten Rechenlaufs** vollständig und fortlaufend abgeglichen.

Nur der lokale Rechner mit den Originaldaten darf diesen Vorgang ausführen.
**Keine Kunden-ZIPs, Bilddateien, Kamerakoordinaten, SQLite-Daten oder
privaten Pfade in GitHub/CI hochladen.**

## Voraussetzungen vor dem echten Lauf

- Lokaler Checkout von PR #9; `main` ist absichtlich älter.
- Funktionierendes Projekt-Python 3.11/3.12 mit den bereits festgelegten
  OpenCV-/NumPy-Abhängigkeiten. Keine zusätzlichen Fremd-Photogrammetrie-Backends.
- Alle **sechs** vorhandenen privaten Archive, nicht nur der ältere
  33-Bild-Import. `RGB2.tip` darf bei gültigem ZIP-Inhalt so heißen.
- Eine **vorhandene unabhängig bestätigte** DJI-M3T-RGB-Objektivkalibrierung im
  Schema `mcm.rgb_camera_intrinsics_external.v1`: `lens_calibration_verified:
  true`, nicht leere `calibration_provenance`, echte `fx/fy/cx/cy`,
  `distortion_coefficients`. Die bekannte Brennweite von 4,4 mm allein
  erfüllt diese Voraussetzung ausdrücklich **nicht**. Keine Test- oder
  Schätzwerte als „verifiziert“ markieren.
- Ein bereits vorhandener privater Ausgabepfad in einem **anderen Verzeichnis**
  als alle Originalarchive. Eine noch nicht vorhandene Berichtdatei verwenden.

## PowerShell-Aufruf (Platzhalter nur lokal ersetzen)

```powershell
# Diese sechs Pfade NUR lokal mit den vorhandenen Archivpfaden befüllen.
$rgbArchivePaths = @(
  'C:\PRIVATE\archiv-1.zip',
  'C:\PRIVATE\archiv-2.tip',
  'C:\PRIVATE\archiv-3.zip',
  'C:\PRIVATE\archiv-4.zip',
  'C:\PRIVATE\archiv-5.zip',
  'C:\PRIVATE\archiv-6.zip'
)
$verifiedCalibration = 'C:\PRIVATE\verified-rgb-lens.json'
$privateReport = 'C:\PRIVATE-RESULTS\rgb-160-quality-report.json'

$cliArgs = @('-m', 'mcm_solarcheck.services.rgb_zip_whole_flight_cli')
foreach ($archive in $rgbArchivePaths) {
  $cliArgs += @('--rgb-archive', $archive)
}
$cliArgs += @('--calibration-json', $verifiedCalibration,
              '--report', $privateReport)
# Die erwarteten 6 Archive und V-0001 ... V-0160 sind bereits feste Defaults.
$env:PYTHONPATH = 'src'
python @cliArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host 'Pruefgate nicht bestanden: nur aggregierten lokalen Report ansehen.'
}
```

Dieser Aufruf **extrahiert keine** ZIP-Mitglieder auf die Festplatte,
verändert keine Originale und schreibt keine SQLite. Der **einzige**
geplante Schreibzugriff ist der angegebene neue lokale JSON-Bericht.

## Falls ein einzelnes Kamerabild das Qualitätsgate nicht besteht

Auch beim Scheitern ist der **neue lokale JSON-Bericht** vorhanden
(sofern `--report` auf eine noch freie Datei zeigt). Dann gilt
`status=whole_flight_rgb_quality_gate_failed` und der CLI-Exitcode ist **2**.
Falls `failed_stage=rtk_weighted_ba` und die einzelne Kamera-p95-Prüfung
fehlgeschlagen ist, enthält der Bericht zusätzlich `per_camera_reprojection`
mit `cameras_above_p95_limit`, `camera_p95_limit_px`,
`worst_camera_reprojection_p95_px`, `all_camera_reprojection_p95_px` und
`all_camera_reprojection_max_px`. `camera_reprojection_quality_passed=false`
bleibt zwingend. **Keine Bild-ID, Position, Originalaufnahme oder Landmark**
wird in diesen JSON-Zusatz geschrieben.

Einige andere Fehler (z. B. fehlende Kalibrierung, unvollständiges
Bildarchiv, nicht zusammenhängende 3D-Spuren oder negative Tiefen) liefern
weiterhin nur einen **anonymen Fehlerabschnitt**, ohne Pixelwerte.
Keines dieser Scheitern darf durch eine nachträgliche Änderung der
6-Pixel-Grenze oder Wiederholung des alten 2D-Stitching kaschiert werden.
Einen lokalen Fehlerbericht gegebenenfalls **nur anonymisiert** teilen;
private Pfade, GPS, DJI-XMP und JPEG-Originale niemals in PR-/CI-Logs stellen.

## Aussagegrenzen des Berichts

`required_flight_coverage_verified=true` besagt nur, dass beim Lauf
sechs Archive und **exakt** die fortlaufenden IDs 0001–0160 verarbeitet
wurden. Das ist keine Aussage über Bildüberlappung oder Orthofotoqualität.
Sukzessive Gates: unabhängige Kalibrierung → Merkmale → ORB-Paare →
kalibrierte SfM-Geometrie des gesamten zusammenhängenden Graphen →
unskalierte Fenster-BA → robuste RTK-priorisierte Fenster-BA und interne
Hold-out-Residuen. Bei Fehler enthält der Bericht nur den anonymen
`failed_stage`, niemals private Bild-IDs oder Koordinaten.

**Eine grüne CI oder ein erfolgreich beendeter Rechenlauf ist keine
Dach-/Survey-/RGB-Orthofoto-/PV-/Thermal-Fachfreigabe.** DJI-RTK-Hold-outs
sind keine unabhängigen vermessenen GCPs. Die 3D-Dachflächen und echte
geneigte Orthorektifizierung müssen danach gesondert entwickelt und
geprüft werden.

**ODM / WebODM / ODX NICHT integrieren. Kein Merge auf `main`
ohne ausdrückliche Nutzerentscheidung.**
