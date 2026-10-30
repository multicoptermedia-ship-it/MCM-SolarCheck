# Privater 160-RGB-Gesamtflug: Windows-10-Read-only-Lauf

**Stand: 30.10.2026 – Entwicklungskandidat auf Draft PR #9.** Status und Sicherheitsgrenzen: [AKTUELLER_ENTWICKLUNGSSTAND.md](AKTUELLER_ENTWICKLUNGSSTAND.md).

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

## Optional: gemeinsam ausgerichtetes privates RGB-Mehrflächen-Prüfbild (30.10.2026)

Der **Standardaufruf oben bleibt reiner Qualitätsbericht**. Erst mit einer
**ausdrücklichen zusätzlichen Option** verwendet das CLI unmittelbar nach
bestandener SfM-/RTK-BA die bereits implementierte automatische Kameraauswahl,
RGB-Orthorektifizierung pro geneigter 3D-Ebenenhypothese und gemeinsame
metrische Rasterzusammenführung. Die BA-Geometrie bleibt im selben Prozess im
RAM. Die Funktion benötigt **mindestens zwei** zulässige Flächenhypothesen.

Bei gewünschtem Prüfbild diese Optionen **in den obigen PowerShell-Block
direkt vor die dortige Zeile `python @cliArgs` einfügen**. Den kompletten
160-Bild-Rechenlauf **nur einmal** starten (nicht erst den Standardaufruf und
danach die komplette Rekonstruktion ein zweites Mal):

```powershell
# Neuen Dateinamen verwenden; der Ordner muss bereits privat existieren.
$privatePreview = 'C:\PRIVATE-RESULTS\rgb-160-unverified-preview.png'
$cliArgs += @('--private-preview-png', $privatePreview,
              '--preview-meters-per-pixel', '0.05',
              '--preview-max-side', '1024')
# Anschließend mit dem `python @cliArgs` aus dem Hauptblock EINMAL rechnen.
```

**Wichtig:** Die separate PNG-Datei darf weder im Git-Checkout noch
im Original-ZIP-Verzeichnis stehen, muss einen absoluten bislang nicht
existierenden Pfad in einem bereits vorhandenen privaten Verzeichnis haben.
Mit `--private-preview-png` ist `--report` Pflicht. Das Bild ist
**RGBA**, ungültige und überlappende unklare Pixels sind transparent und
deren verborgene RGB-Kanäle schwarz. **Keine ENU-Koordinaten oder GPS-Metadaten
im PNG.** Der vollständige private Bildinhalt verlässt den lokalen Rechner
nicht; niemals PNG oder Originalarchive nach GitHub/CI hochladen.

Wenn der komplette BA-Lauf gut ist, aber der Mehrflächen-Renderer scheitert
oder kein gültiger Pixel vorhanden ist: **Exit 2**, anonymes
`failed_stage=multiplane_preview`, `private_preview_png_written=false`;
kein neues PNG. Nach erfolgreichem Rendering erscheinen nur aggregierte
`private_multiplane_preview`-Werte und
`private_preview_png_written=true` im lokalen JSON. Ein optisch überzeugendes
Preview ist **noch keine** freigegebene Dachfläche, echte Okklusions-,
Naht-/GSD-/Survey-/RGB-Orthofoto-/PV-/Thermalprüfung. Die automatische
Quellkameraauswahl ist projektiv, keine bereits bewiesene Sichtbarkeit.

Dieser Standardaufruf **extrahiert keine** ZIP-Mitglieder auf die Festplatte,
verändert keine Originale und schreibt keine SQLite. Der **einzige**
geplante Schreibzugriff ist der angegebene neue lokale JSON-Bericht.

## SfM-Feature-Tracks: widersprüchliche Bildverknüpfungen

Auch ein kalibriert per Essential-RANSAC/Pose akzeptiertes Bildpaar ist nur
dann brauchbare Mehrbild-Track-Evidenz, wenn jeder beteiligte ORB-Keypoint
pro Bildpaar **eindeutig** zugeordnet ist. Die aktuelle SfM-Implementierung
lehnt one-to-many-Keypoint-Zuordnungen schon vor der Triangulation ab; bei
mehr als einem Drittel widersprüchlicher Track-Verschmelzungen in einem
akzeptierten Bildpaar oder insgesamt stoppt sie am `global_sfm`-Gate.
Ein solcher Fehler darf nicht durch bloßes Ignorieren der konflikthaften
Merkmalspaare zu einem „guten“ Dachmodell umgedeutet werden.

Im erfolgreichen Diagnosebericht stehen
`sfm_track_conflicting_merges_rejected` und
`sfm_accepted_geometric_feature_correspondences`. Beide Zahlen sind
**aggregiert**, ohne Keypoint-, Frame-, Kamera- oder Weltkoordinaten. Bei
`failed_stage=global_sfm` werden wie bisher nur anonymisierte
Fehlerstufe und Nichtfreigabe geschrieben; keine vertraulichen
Merkmals- oder GPS-Daten für den Fehlersuchlauf in CI hochladen.

## Auch der gemeinsame 3D-Trackgraph muss verbunden sein

Ein über Essential-RANSAC akzeptiertes Kamerapaar allein genügt noch nicht:
Nach dem SfM-Triangulieren müssen dieselben beiden Kameras mindestens
**acht unterschiedliche tatsächlich behaltene 3D-Punkt-IDs** teilen, damit
ihre Verbindung im 3D-Trackgraphen zählt. Die durch diese 3D-Punkte
bestätigten Kameraverbindungen müssen **alle 160 Kameras** umfassen;
mindestens zwei räumlich nichtbenachbarte, durch gemeinsame 3D-Punkte
bestätigte Verbindungen müssen mindestens drei Kameras beteiligen.

Ein Scheitern führt zum anonymen `failed_stage=global_sfm` und Exit 2,
**bevor** die aufwendige Fenster-/RTK-Bundle-Adjustment beginnt. Bei
erfolgreichem Durchlauf stehen nur die aggregierten Felder
`sfm_3d_track_graph_connected`,
`sfm_3d_supported_pair_count`,
`sfm_3d_weak_geometric_pair_count` und
`sfm_3d_supported_spatial_nonadjacent_pairs` im lokalen JSON.
Keine Bild-IDs, Koordinaten, Kameraposen oder private Trackdetails werden
ausgegeben; die 3D-Punktübereinstimmung allein beweist außerdem weder
physische Flugstreifenzugehörigkeit noch Dach-/Surveygenauigkeit.

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

## Falls trotz guter Pixelwerte die 3D-Tiefenstützung zu schwach ist

Nach der Einzelkamera-Reprojektion prüft das neue
`rgb_multiview_parallax_gate.py` die Sichtstrahltrennung mehrerer Kameras
für alle behaltenen 3D-Punkte. Standardmäßig müssen wenigstens 75 % der
Punkte aus mindestens zwei **verschiedenen** Kameras mit einer konservativen
Winkeluntergrenze von 0,25° gestützt sein. Zusätzlich muss **jede Kamera**
mindestens **25 % ihrer 3D-Beobachtungen** auf solchen stark triangulierten
Punkten haben. Damit kann eine schwache Bildgruppe nicht von einem sonst guten
Gesamtflug verdeckt werden. Kameras ohne jegliche 3D-Beobachtung scheitern.
Dieses Gate prüft lediglich Photogrammetrie-Parallaxe,
**keine unabhängige GCP-/Dachgenauigkeit**.

Beim Scheitern steht `status=whole_flight_rgb_quality_gate_failed`,
`failed_stage=rtk_weighted_ba`, Exitcode **2** und zusätzlich
`multiview_parallax` im nur lokal gespeicherten JSON. Die Felder
`supported_landmark_count`, `weak_landmark_count`,
`supported_landmark_fraction`, `landmark_parallax_p10_deg`,
`landmark_parallax_median_deg`,
`cameras_below_supported_observation_fraction` und
`worst_camera_supported_observation_fraction` enthalten **nur Aggregate**; die realen
Punkt-/Kamerakoordinaten bleiben im Arbeitsspeicher. `parallax_quality_passed`
ist ausdrücklich `false`, selbst wenn die Kameras pixelweise gut passen.
Bei echtem Versagen **nicht** einfach den Winkelgrenzwert absenken.

## Erste vertikale 3D-Geometrieresultate (nur Hypothesen)

Nach dem RTK-gewichteten Bundle Adjustment und den bestehenden Pixel- und
Parallaxenprüfungen passt der lokale Algorithmus mit RANSAC+SVD erstmals
**geneigte Ebenenhypothesen an tatsächlich rekonstruierte metrische 3D-Punkte**
an. Im nur lokal gespeicherten Bericht stehen diese Werte unter
`rtk_windowed_ba.pitched_plane_hypotheses`:
`plane_candidate_count`, `total_supported_landmarks`,
`candidate_slope_min_deg`, `candidate_slope_max_deg` und
`worst_candidate_plane_residual_p95_m`. Die privaten Ebenennormalen,
Höhen-/Abstandsparameter, Stützpunkt-IDs und XY-Footprints werden
**nicht als JSON exportiert**. Sie bleiben ausschließlich im in-memory
BA-Objekt für die anschließende Entwicklung der echten Dachorthorektifizierung.

**0 Hypothesen ist kein erkanntes Dach; auch mehrere Ebenenhypothesen sind
keine verifizierten Dachflächen.** Sie könnten ebenso geneigtes Gelände
oder andere Flächen sein. Keine Survey-/Dachflächen-/Ortho-/PV-/Thermalfreigabe
und kein Export angeblicher georeferenzierter Dachpolygone. Lokale echte
160-Kamera-Bilddaten sind weiterhin notwendig, bevor man die Geometrie
fachlich gegen reale Dachflächen prüfen kann.

## Mehrere geneigte Flächen im selben privaten RGB-Vorschauraster

Der neue **optionale In-Memory-Preview**, nicht der automatische 160-RGB-CLI-
Produktexport, setzt mehrere bereits im erfolgreichen RTK-BA-Objekt vorhandene
geneigte 3D-Kandidaten in ein gemeinsames metrisches **nordorientiertes**
ENU-RGB-Raster. `render_private_multiplane_preview_from_original_rgb_archives`
wählt pro Kandidat automatisch 2–8 Kameras anhand der **finalen optimierten
BA-Posen, echten externen Intrinsics und des projizierten 3D-Footprints**
aus, dekodiert nur deren Originale direkt aus den bekannten ZIP/`.tip`-
Archiven, entzerrt mit der verifizierten Kalibrierung und projiziert RGB
auf die jeweilige geneigte Fläche. Keine ZIP-Extraktion, keine Original- oder
SQLite-Veränderung, **kein** Bilddateiexport durch diese Funktion. Die
Funktion benötigt das tatsächlich noch im Arbeitsspeicher befindliche
`PrivateRGBRTKWindowedBA`-Objekt und ist daher **nicht** mit einem
bereits gespeicherten CLI-JSON allein aufrufbar. Keine Optik-Kalibrierung
aus EXIF schätzen.

Die Rastermaske enthält nur gültige, wirklich projizierbare Pixel. Bei
überlappenden Flächenhypothesen wird **nicht** blind gemittelt: Liegen ihre
Z-Höhen weniger als 0,15 m auseinander, bleiben solche Übergangspixel
`ambiguous_overlap_mask_private` und damit ungültig. Das ist eine
konservative Preview-Heuristik, **keine** physikalische Okklusionslösung
und **keine** verifizierte Dachkante. In der anonymen privaten
`privacy_safe_summary()` erscheinen allein Anzahl Kandidaten,
Quellkameras sowie gültige/mehrdeutige Pixelanteile; tatsächliche RGB-Daten,
ENU-Lage, Posen und Dachpolygone niemals im CLI/CI-Log.

Das nächste reale Ziel bleibt **der komplette lokale 160-Bild-Lauf** mit
geprüfter externer Objektivkalibrierung; erst daraus können reale Flächen
und Übergänge beurteilt werden. Bis zur unabhängigen Dach-/Naht-/
Geometrieprüfung weiterhin **kein** Dachorthofoto-/PV-/Thermal-PASS.

## Modellierte Sichtbarkeit benachbarter Flächen (30.10.2026)

Der opt-in private Mehrflächen-Preview verwendet jetzt zusätzlich die
**anderen rekonstruierten geneigten Ebenenhypothesen als geometrische
Sichtstrahl-Hindernisse**: Eine Kamera darf einen Zielpixel nicht liefern,
wenn ihr finaler BA-ENU-Kamera→3D-Zielpunkt-Strahl **vor** dem Ziel eine
andere Plane innerhalb ihrer privaten konvexen XY-Hülle schneidet. Bleiben
keine Quellen übrig, bleibt der Pixel transparent. Einzelne blockierte
Quellen dürfen nicht als Geisterbild in eine unverdeckte Kamera gemittelt
werden. Es sind keine weiteren PowerShell-Optionen nötig; der opt-in-Aufruf
oben bleibt gültig.

**Keine physisch validierte Sichtbarkeit:** Die Planes sind bislang nur
unbestätigte metrische Hypothesen, unbekannte Gebäude- oder PV-Objekte
bleiben unberücksichtigt. Dachgrenzen, GSD, Nahtqualität, externe Survey-
und RGB-Orthofoto-/PV-/Thermalfreigaben weiterhin **nicht** bestanden.
CI-/synthetische Verdeckungstests belegen keine reale Dachszene.

## RGB-Geisterbilder reduzieren: automatische Quellpriorität (30.10.2026)

Der opt-in **Mehrflächen**-Preview verwendet jetzt automatisch die
reihenfolgestabile `source_fusion="priority"`: Pro Zielpixel wird die
**erste tatsächlich sichtbare** der bereits geometrisch ausgewählten
RGB-Kameras verwendet. Die übrigen Quellen füllen nur geometrische
Abdeckungslücken oder Kandidaten-Verdeckungen, statt Farbwerte
mehrerer leicht gegeneinander versetzter Bilder zu mitteln.

**Keine Änderung am PowerShell-Aufruf nötig.** Der Standardlauf ohne
`--private-preview-png` bleibt reiner anonymisierter Qualitätsbericht.
Explizite Einzelpatch-Diagnosen können weiterhin den alten Mittelwert
benutzen. Die in der privaten Renderer-Zusammenfassung gemeldeten
sekundären Bildpixel sind eine reine Zahl, keine Quell-IDs oder Positionen.
**Wichtig:** Quellwechsel können farbliche/sichtbare Nähte erzeugen; keine
echte Photometrie-Korrektur, nahtoptimierende Seamline, validierte
Dachabgrenzung oder GSD-/Survey-/Orthofoto-Freigabe. Zuerst 160 echte
RGB-Originale mit unabhängiger Kalibrierung privat durchrechnen, danach
die echten Dachraster und Übergänge prüfen. Keine Originaldaten hochladen.

## Überdeckungsbasierte Farbkorrektur bei Kameraübergängen (30.10.2026)

Das optionale private Mehrflächen-RGB-PNG nutzt im bestehenden automatischen
Renderer jetzt `source_fusion="priority_overlap"` ohne neue Parameter.
Weiterhin bildet **eine** Kamerasicht den Pixel und damit keine
Mehrfachbild-Mittelung. Bei der nachfolgenden Quellkamera werden allerdings
kleine Helligkeits-/Farbunterschiede ausgeglichen, **nur wenn** sie auf
denselben echten 3D-Punkten einer geneigten Kandidatenfläche innerhalb
einer ausreichend großen, sichtbaren und nicht übersteuerten
Quellbildüberlappung robust nachweisbar sind.

Für die automatisierte Anpassung benötigt der Renderer mindestens 128
geeignete Pixel, testet höchstens 4096 deterministische Samples und
akzeptiert nur einen geringen Kanal-Offset (≤24 RGB-Stufen) mit niedriger
Abweichung (MAD ≤12). **Bei schwacher, fehlender oder widersprüchlicher
Überdeckung bleibt das zweite Quellbild unverändert**, statt aus
unpassenden Flächen vermeintliche Farbkorrekturen zu erfinden. Ungültige
Pixel bleiben transparent, die Originalarchive und Kalibrierdaten
unangetastet. Die privaten Summenfelder
`radiometric_corrected_source_count` und
`radiometric_overlap_support_pixels` enthalten ausschließlich
aggregierte Zahlen, keine Kameranamen, Farben, Positionen oder GPS.

Das ist eine konservative **Vorschau-Nahthilfe**, kein photometrisch
freigegebenes nahtfreies Dachorthofoto. Die echten 160 RGB-Originale plus
unabhängig nachgewiesene DJI-RGB-Linse müssen privat offline durchlaufen;
Dachgrenzen, physische Okklusion, Nachbarbild-Nähte, GSD, independent
Survey, PV-Module und Thermal bleiben ungeprüft.

## Farbkorrektur jetzt nur direkt am Kameranahtwechsel (30.10.2026)

Der vorhandene opt-in Mehrflächen-PNG-Renderer (`priority_overlap`)
nutzt ab Code `ec44f1b` die echte geometrische Quelle→Fallback-Grenze:
Für einen robusten kleinen RGB-Farb-Offset zählen ausschließlich
verifizierbar gemeinsam in dasselbe geneigte 3D-Plane-Raster projizierte
und innerhalb **7 Zielpixeln** der neu ergänzten Fallback-Zone liegende
Pixelevidenzen. Gültige gemeinsame Überdeckungsbereiche werden zuvor
an ihrem Rand um 1 Pixel erodiert; räumlich weit entfernte
Überdeckung bei anderen Lichtverhältnissen wird nicht mehr benutzt.
Damit wird ein Wechsel der Beleuchtung innerhalb desselben Dachbilds
nicht durch einen globalen Offset verschlechtert.

Wie bisher gilt: mindestens **128** ungesättigte, konsistente
RGB-Nahnaht-Pixel, maximal 4096 Samples, Kanaloffset höchstens
±24 und MAD höchstens 12. **Fehlt eine gute lokale Überdeckung,
bleibt die sekundäre Kamera unverändert.** Die erste Quellkamera und
alle Masken bleiben unberührt; kein Vermischen von Kamerapixeln.
Keine zusätzlichen CLI-Optionen, Originaldateien weiterhin read-only.
Die aggregierten Korrektur-Supportzahlen im privaten JSON meinen
nun speziell die tatsächlich nahtnahen Bildpixel, keine GPS-/Quell-IDs.

Dies ist eine geometrisch abgestützte Vorschau-Farbkorrektur und
**keine** reale Naht-/Dach-/Ortho-/GSD-/Survey-/PV-/Thermal-Abnahme.
Die echte Beurteilung erfordert weiterhin den privaten Windows-
Komplettflug mit allen 160 DJI-RGB-Originalen und nachgewiesener
externer DJI-M3T-Objektivkalibrierung.

## Geometrisch erfasste RGB-Nähte im lokalen Privatreport (30.10.2026)

Beim **opt-in** privaten Mehrflächen-PNG (`--private-preview-png`)
erzeugt der bereits bestehende Renderer jetzt auch anonymisierte
Nahtindikatoren im lokalen JSON-Feld `private_multiplane_preview`.
Dafür zählt er auf tatsächlich gerenderten und **beidseitig gültigen**
4-Nachbar-Pixelpaaren die Quellwechsel: zwischen **zwei Kameras
innerhalb einer geneigten Ebene** sowie separat zwischen **zwei
verschiedenen geneigten Ebenenhypothesen** im gemeinsamen ENU-Raster.

Im privaten JSON sind das die Felder
`candidate_camera_seam_boundary_pairs`,
`worst_candidate_camera_seam_rgb_jump_p95`,
`candidate_facet_transition_boundary_pairs` und
`candidate_facet_transition_rgb_jump_p95`.
Der p95-Wert misst den **95. Perzentilwert des größten
RGB-Kanalbetrags der Differenz** zwischen den gültigen benachbarten
Zielpixeln (0 bis 255). Er ist **null**, wenn kein solcher
Übergang vorliegt. Das ist ein lokaler **Prüfhinweis**, keine
vorgegebene Freigabeschwelle. Hohe Werte können echte
Dach-, Gauben- und PV-Kontraste sein; niedrige Werte beweisen
keine korrekte Dachgeometrie, GSD oder ausgeblendete Doppelbilder.

Die Kamera- und Flächen-Indexkarten bleiben vollständig in RAM,
kein Kameraindex, Pixel, Bild, privater Pfad, ENU- oder GPS-Wert
wird durch diese Diagnostik ausgegeben. Keine zusätzlichen Dateien,
keine neuen PowerShell-Parameter; der normale Lauf ohne
privates PNG bleibt wie zuvor ausschließlich aggregiert.
Die echten 160 RGB-Originale und unabhängig bestätigte
DJI-RGB-Objektivkalibrierung werden weiterhin **nur lokal** verarbeitet.
Die Orthofoto-/Roof-/GSD-/Survey-/PV-/Thermalqualität ist
damit **nicht** freigegeben.

## Dachflächenvorschau nur bei tatsächlicher 3D-Punktstützung (30.10.2026)

Der bestehende private, opt-in `--private-preview-png`-Lauf behält ab
Code `22650686` die **tatsächlichen optimierten 3D-Inlier-Punkte**
der geneigten Ebenenhypothesen ausschließlich im RAM. Früher konnte
eine konvexe Hülle zwischen auseinanderliegenden Punktgruppen trotz
fehlender 3D-Messstützung als vollständige Dachfläche gerendert werden.
Jetzt sind nur Pixel innerhalb des bisher geprüften Footprints **und**
in einer metrisch begrenzten Nachbarschaft zu diesen wirklichen
triangulierten Punkten gültig. Der maximale Abstand wird aus Fläche
und Punktzahl berechnet und auf **0,35 bis 1,5 m** begrenzt. Deutlich
ungestützte Bereiche bleiben **RGBA-transparent**; keine erfundenen
Dach- oder PV-Pixel.

Das private JSON-Feld `private_multiplane_preview` enthält dafür die
reine Gesamtzahl `unsupported_convex_hull_pixels`. Die 3D-Punkte,
Kamera-IDs, Polygon- und ENU-/GPS-Koordinaten werden weder exportiert
noch in der Konsole angezeigt. Keine neuen CLI-Optionen, Abhängigkeiten
oder Dateiänderungen an den sechs Original-ZIP/`.tip`-Archiven.

**Einordnung:** Ohne SfM-Merkmale bleiben eventuell auch echte,
texturarme Dach-/PV-Bereiche transparent. Die 3D-Stützung ist eine
vorsichtige Hypothesen-Abdeckung, **keine** verifizierte reale Dachkante
oder unabhängige GSD-/Survey-/Orthofoto-/PV-/Thermalfreigabe. Bei der
echten 160-RGB-Vor-Ort-Rekonstruktion das private PNG und den
aggregierten Bericht gemeinsam beurteilen, keine Originalbilder
oder GPS-/Kalibrierungsdaten nach GitHub hochladen.

## Kandidaten-Verdeckung nur bei tatsächlicher 3D-Stützung (30.10.2026)

Ab Code `a149edd8` nutzt die vorhandene private
`--private-preview-png`-Mehrflächenprojektion die bereits
rekonstruierten 3D-Inlier-XY nicht nur für die gültige **Ziel-RGB-Fläche**,
sondern auch bei der Prüfung **verdeckt eine andere geneigte
Flächenhypothese das betreffende Quellbild?**

Wichtig: Eine konvexe Hülle allein ist keine durchgehende Dachfläche.
Ein Kamera-Sichtstrahl gilt bei tatsächlichen rekonstruierten
Kandidaten jetzt nur dann als durch eine andere Plane blockiert, wenn
sein Schnittpunkt innerhalb von deren Hülle **und** ausreichend nahe
an deren tatsächlich triangulierten, metrisch optimierten 3D-Punkten
liegt. Der Abstand folgt der bestehenden dichteabhängigen Heuristik
von **0,35 bis 1,5 m**. Eine begrenzte private OpenCV-Distanzkarte mit
konservativer Zell-Sicherheitsmarge bewertet diese Nachbarschaft.
Große ungestützte konvexe Zwischenräume löschen somit nicht länger
willkürlich sichtbare RGB-Zielpixel. Physisch weiter entfernte oder
nicht rekonstruierte Hindernisse bleiben jedoch **unbekannt**.

Es gibt dafür **keine zusätzlichen CLI-Optionen** und keine neuen
Schreibzugriffe. Die sechs Original-ZIP/`.tip`-Archive bleiben
read-only, Pixel-/3D-Inlier-/GPS-/ENU-Daten im privaten RAM.
Die bestehenden anonymisierten Aggregatwerte bleiben erhalten.
Auch mit dieser Korrektur ist das Mehrflächen-PNG **keine** geprüfte
reale Dach-/Occludergrenze und keine vermessene GSD-, RGB-Ortho-,
PV- oder Thermal-Freigabe. Im echten privaten Windows-Lauf das
gesamte 160-JPEG-Ergebnis visuell prüfen; ein synthetischer CI-Erfolg
ersetzt diesen Nachweis nicht.

## Quellkameras werden nach tatsächlich gestützter und sichtbarer 3D-Fläche gewählt (30.10.2026)

Mit Code `ae435e65` wird die Quellkameraauswahl **vor dem privaten
Original-JPEG-Decoding** konsistent zur bestehenden Dachprojektion.
Vorher genügten 9×9 projizierte Rasterpunkte in der gesamten konvexen
Dachkandidaten-Hülle. Dadurch konnte eine Kamera ausgewählt werden,
deren vermeintliche Dachfläche durch fehlende rekonstruierte 3D-Punkte
oder durch eine höher gelegene Kandidatenfläche später in Wirklichkeit
nicht in das RGB-Preview einging.

Nun prüft die Kameraauswahl ein **25×25-Punkte-Gitter** auf der
jeweiligen geneigten metrischen Ebene und nutzt die echten BA-
rekonstruierten 3D-Inlier-Stützbereiche (ab `22650686`). Für bis
zu 32 geometrisch geeignete Kamerakandidaten wird außerdem die
modellierte, 3D-punktgestützte Verdeckung durch andere Flächen-
hypothesen (ab `a149edd8`) berücksichtigt. Erst danach wählt
sie 2 bis 8 Quellkameras nach zusätzlicher sichtbarer Zielabdeckung
und unterschiedlicher Kamerabasis. Beim fehlenden Nachweis von zwei
geeigneten Blickwinkeln wird **abgebrochen**, statt eine Dachaufnahme
vorzutäuschen. Der bisherige einzeln priorisierte RGB-Quellpixel-
Renderer und die private RGBA-Transparenz bleiben erhalten.

Keine neue CLI-Option, kein neues Dateiformat und kein Zugriff auf
externe Anbieter; alle sechs Original-ZIP/`.tip`-Archive weiterhin
read-only. Die Kandidaten- und Stützpunktgeometrie bleibt im RAM.
**25×25-Stichproben und die max.-32-Kamera-Shortlist sind Heuristiken**,
keine unabhängige reale Sicht-/Dach-/Naht-/GSD-/Orthofoto-/
PV-/Thermal-Freigabe. Lokalen kompletten 160-RGB-Privatflug mit
unabhängig nachgewiesener DJI-Objektivkalibrierung durchführen und
erst dann tatsächliche PV-/Dach-RGB-Bildschärfe/Masken beurteilen.

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
