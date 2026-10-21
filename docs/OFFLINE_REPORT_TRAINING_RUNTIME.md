# Kontrollierte lokale KI-Trainingsaufträge nach SolarCheck-Berichtsfreigabe

## Tatsächlicher Stand, 21.10.2026

Die Offline-Berichtsfreigabe enthält den **standardmäßig ausgeschalteten** Schalter
„solarcheck-Datensatz für das KI-Training freigeben“. Eine ausgewählte
Trainingsfreigabe erfordert eine gesonderte Referenz für nachgewiesene Rechte;
der genaue Nachweis und seine Rechtsgültigkeit müssen fachlich überprüft werden.
Berichtsfreigabe und Trainingsnutzung bleiben unabhängig. Nur zuvor in SQLite
als `human_reviewed` und `rights_status=approved` gespeicherte Trainings-Samples
dürfen mit Hashprüfung in den privaten lokalen Trainingsordner gelangen.

Dieser Entwicklungsblock ergänzt die **konditionale lokale Ausführung** mit
`OfflineTrainingJobs`. Sobald und **nur wenn** eine geprüfte
`OfflineTrainerConfiguration` **und** ein vertrauenswürdig bereitgestellter,
kooperativer `training_launcher` in `build_offline_window(...)` injiziert wurden,
versucht die Trainingsanfrage automatisch die Vorprüfung und startet einen
Hintergrundauftrag. Die tatsächlich ausgelieferte Standard-Composition
konfiguriert **keinen** Trainer, keine Gewichte und keinen Modell-Download.
Deshalb wird bei einer unveränderten regulären Windows-10-Installation noch
**kein echtes KI-Modell trainiert**. Ein Trainingswunsch verbleibt
`pending_training_data_review` oder `staged_waiting_for_trainer`.

## Voraussetzungen vor jedem Start

- Eine explizit gültige, unveränderte fachliche Berichtsfreigabe und freiwillige
  projektbezogene Trainingsfreigabe. Der bloße PDF-Scroll-Endpunkt bestätigt
  weder menschliches Lesen noch Trainingserlaubnis.
- Separat für Training menschlich geprüfte und für diese Nutzung freigegebene
  Daten. Die vorläufige Nutzungsrechts-Referenz im UI ist noch kein geprüfter
  Vertrag oder DSGVO-Nachweis.
- Mindestens sechs geprüfte, lokal verfügbare Klassifikationsbeispiele,
  mindestens zwei Klassen und **drei** tatsächlich vorhandene, gruppengetrennte
  Splits `train`, `validation`, `test`. Gruppen werden im privaten Index
  nur pseudonym per SHA-256 mit anfragespezifischem Bezug gespeichert; keine
  ursprünglichen Pfade oder Kundenstammdaten im abgelegten `training-index.json`.
- Jedes Bild wird vor dem Jobstart sowie unmittelbar im Hintergrundthread
  erneut über die Original-Hashangabe verifiziert. Unbekannte Bilder, Symlinks,
  defekte Quellen, falscher Split, Gruppenüberschneidung und nicht freigegebene
  Trainingsbilder blockieren die Verarbeitung.
- Ein ausdrücklich geprüfter und tatsächlich auf der Zielmaschine vorhandener
  Modellcheckpoint (`.pt`) mit vorgegebenem SHA-256, dokumentierter
  Lizenzprüfreferenz, Backend-/Versionsbezeichnung, Seed und Epochengrenze;
  kein automatisch geladenes Modell. Ein textuelles Prüfreferenzfeld
  **ersetzt weder** die sachliche Lizenzprüfung **noch** ein zulässiges Modell.
- Der bestehende private Trainingsindex enthält nur Klassifikationsklassen.
  **Keine** geprüften YOLO-Boxen, Polygone oder radiometrischen Temperaturziele
  werden dadurch erzeugt. Ohne separate Datenaufbereitung/Annotation darf
  keine echte YOLO-Detektions- oder Segmentierungsausführung vorgetäuscht werden.

## Jobzustände und Sicherheitsgrenzen

`OfflineTrainingJobs` speichert pro Trainingsanfrage in der bestehenden privaten
Trainings-SQLite einen Fortschrittseintrag mit Prozentsatz, Zeitpunkt, optionaler
SHA-256 der erzeugten Modell-Datei und generischem Fehlercode. Die
Trainingsanfrage wechselt atomar von `staged_waiting_for_trainer` auf
`training_running`. Der ausdrücklich eingestellte vertrauenswürdige Backend-
Aufruf erfolgt im **Hintergrundthread**, erhält nur geprüfte lokale Daten, die
Konfiguration, einen privaten Ausgabeordner, ein Fortschrittscallback und ein
kooperatives Abbruchsignal. Ein gültiges Ergebnis muss eine lokale, beschränkte
`.pt`-Datei im exklusiven privaten Ausgabeordner sein. Danach lautet der
Status `training_completed_not_deployed`: **keine automatische
Modellaktivierung, keine wissenschaftliche Validierung, keine Aussage zu
Temperaturkalibrierung oder PV-Defektzuverlässigkeit**.

Andere Zustände: `training_failed` (generischer Fehlercode, niemals
Ausnahmetext mit Kunden-/Dateipfaden), `training_cancelled` und `revoked`
(Trainingseinwilligung widerrufen). Ein Widerruf setzt die Berechtigung auf
`revoked`, signalisiert einem aktiven lokalen Thread den Abbruch und entfernt
lokale Trainingskopien nach dem kooperativen Stop. **Harte Prozessbeendigung
eines nicht kooperativen Backends ist noch nicht implementiert**; bis dahin
kann die Bereinigung verzögert sein. Neustart, Stromausfall und Fremdprozess-
Konkurrenz werden noch nicht als belastbar wiederaufgenommene Jobs behandelt.
Der gespeicherte Status `training_running` ist nach einem Programmneustart
**kein Beweis**, dass der Trainer noch aktiv arbeitet. Bereits trainierte
Modelle können durch nachträglichen Widerruf nicht automatisch „entlernt“
werden. Backend-Plugins dürfen insbesondere nicht ohne gesonderte Prüfung
Netzwerkanfragen, Autodownloads oder externe Modellveröffentlichung durchführen.

## UI und Tests

Die Berichtseite zeigt den persistierten wirklichen Stand des eigenen Projekts,
bietet „Trainingsstatus aktualisieren“ und weiterhin
„KI-Trainingsfreigabe widerrufen“. Berichtsfreigabe und normaler Export sind
davon unabhängig. Die gezielt ergänzten Tests verwenden ausschließlich einen
**synthetischen Backend-Stub**: sechs lokale künstliche JPEGs, getrennte
Gruppen und zwei Klassen, Fortschrittsänderungen, ein Dummy-`.pt`, Fehlersanitierung,
Widerruf während eines laufenden Jobs, Prüfsummenänderung und fehlenden
Checkpoint. Diese Dummy-Datei ist ausdrücklich **kein brauchbares KI-Modell**.
Windows-2022 und Ubuntu Python 3.11/3.12 testen die Zustandsmaschine, nicht
eine echte Windows-10-GPU und nicht ein produktiv trainiertes YOLO-Modell.

## Nächste Freigabeprüfungen

Vor einer produktiven **automatischen** Trainingsausführung sind ein
lizenzrechtlich geprüftes, tatsächlich eingebautes und netzfrei ausführbares
Modell-Backend, validierte Klassifikations- oder YOLO-Annotationsformate,
nachvollziehbare unabhängige Gruppensplits, echte getrennte Testdaten,
Trainingsmetriken, Hardware-/Ressourcengrenzen, prozesssichere
Abbruch-/Wiederaufnahmesemantik, Nutzer-/Kundenrechte, Löschkonzept,
unerwünschte Netzverbindungen und eine eigenständige Modellfreigabe zu prüfen.
Ein bloßer Rückgabewert des Trainings-Backends darf kein reales Modell in die
Berichtserstellung ausrollen.

## 21.10.2026 – nachgelagerter Open-Source-Klassifikationsadapter

Der hier ursprünglich nur injizierbare Trainingsrunner besitzt nun einen
**optionalen echten PyTorch-/TorchVision-CPU-Adapter** ohne gekaufte
Modelle und ohne externe vortrainierte Gewichte. Konkrete Bediener- und
Lizenz-/Paketprüfungen: `docs/OFFLINE_OSS_AI_LICENSE_POLICY.md`.
Nur ausdrücklich lokal initialisierte ResNet18-`state_dict`s samt
passender lokaler SHA-256-/Herkunftsdatei werden vom Adapter
akzeptiert. `weights=None` bei jeder Modellkonstruktion, Laden
ausschließlich mit `weights_only=True`, separate Validierungs-/Test-
Kennzahlen, niemals automatische Kundenmodell-Freigabe. Die normale
Offlineinstallation enthält weder PyTorch noch einen aktiven KI-Trainer.

Vorsicht: Eine lokale JSON-Provenance ist kein signierter Nachweis.
Das Lizenzfeld bestätigt keinen geprüften fremden Vertrag. Der
bereitstehende Adapter kann technisch trainieren, aber die
optional installierten PyTorch-Wheels, echten Windows-10-Mavic-3T-Daten,
Trainingskandidaten und PV-Fachleistung sind hiermit noch nicht
produktseitig abgenommen.
