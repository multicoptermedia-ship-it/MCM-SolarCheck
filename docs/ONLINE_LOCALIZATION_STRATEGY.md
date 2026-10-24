# MCM-SolarCheck Online – europäische Mehrsprachigkeit (i18n/l10n)

Status: **Verbindliche Produktanforderung / Architekturplanung**, noch **nicht** als implementierte Funktion zu verstehen.
Erfasst am: 24.10.2026. Entwicklung weiterhin **offline zuerst**; Online-Architektur vorausschauend sprachneutral gestalten.

## Zielbild

Die spätere Online-Version soll in mehreren europäischen Ländern sinnvoll nutzbar sein.
Die Benutzeroberfläche, Hilfetexte, Freigabe-/Sicherheitshinweise und kundenbezogene
Ausgaben dürfen nicht dauerhaft von deutschen Literaltexten abhängen. Eine Sprache
ist nicht mit einem bestimmten Land oder einer bestimmten Rechtsordnung gleichzusetzen.

## Prioritäten

1. **Startsprachen DE und EN** für die erste internationale Online-Stufe.
   Weitere Sprachen nach Markt- und Nutzerbedarf priorisieren, beispielsweise
   FR, NL, ES, IT und PL. Das sind Optionen, keine bereits gelieferten Sprachpakete.
2. Benutzer können die **Sprache manuell wählen und jederzeit ändern**.
   Erster Vorschlag anhand Browsersprache; optional gespeicherte Kontopräferenz.
   Niemals Sprache ausschließlich aus IP-Adresse, Landeskennzeichen oder Zeitzone ableiten.
   Definierter, sichtbarer Fallback für fehlende Texte (zunächst EN).
3. **Alle sichtbaren Texte** über stabile Übersetzungsschlüssel verwalten:
   Navigation, Formulare, Validierung, Fehlermeldungen, Datenschutz-/Einwilligungsdialoge,
   Verarbeitung und Fortschritt, Review-Sperren, Bericht, Export, Benachrichtigungen,
   Support und Hilfe. Keine teils deutschen, teils englischen technischen Blocker
   im Online-UI; Backend liefert **stabile Fehler-/Blocker-Codes mit Parametern**,
   Clients präsentieren die passende Übersetzung.
4. **Lokalisierte Berichte und Benachrichtigungen** unterstützen:
   sprachabhängige PDF/ODT/DOCX-Texte, E-Mails und Projektdokumente.
   Die Berichtssprache wird **explizit** ausgewählt und für revisionssichere
   Berichtsstände gespeichert; Wechsel der UI-Sprache verändert kein
   bereits freigegebenes Dokument stillschweigend.
5. **Internationalisierung von Daten**:
   Unicode, regionale Datums-/Uhrzeit-/Zahlenformate, Dezimal-/Tausendertrennzeichen,
   Einheiten, Zeitzonen, Plural-/Genusformen und sichere Formatierung variabler
   Texte. Technische Zahlenwerte, Koordinaten, Rohwerte, Kennungen und
   Audit-Historie bleiben unverändert/kanonisch; nur ihre Anzeige wird lokalisiert.
   Zeitstempel werden intern eindeutig (UTC) gespeichert und benutzer-/standortgerecht
   angezeigt. Die Projektsprache und die Zeitzone sind getrennte Einstellungen.
6. **Fachliche Semantik beibehalten**: verbindliches Übersetzungsglossar für
   Thermal-/RGB-Analyse, Temperatur, Anomalien, Befundkandidaten,
   menschliche Fachentscheidung, Unsicherheit, Verarbeitungsstatus und
   Freigabe. Eine Übersetzung darf „unbestätigt“ nicht in „Defekt bestätigt“
   verwandeln. Sicherheitsblocker und Freigabeprüfungen laufen unverändert im
   Backend und werden **niemals** durch eine Übersetzung umgangen.
7. **Qualität & Barrierefreiheit**: professionelle/fachliche Prüfung der
   Übersetzungen; automatische Tests auf fehlende Schlüssel, Platzhalter,
   Pluralfälle, Sonderzeichen, lange Labels/Responsive Layout,
   Screenreader-Labels und Formularfehler; echte sprachspezifische
   Benutzerakzeptanztests. Keine automatische Sprachumstellung während
   einer entscheidungsrelevanten Benutzeraktion.
8. **Juristische Inhalte getrennt regeln**: lokalisierte Nutzungsbedingungen,
   Datenschutzhinweise und etwaige länderspezifische Pflichten benötigen
   geprüfte, versionierte Rechtstexte; reine maschinelle Übersetzung begründet
   keine Compliance.

## Technische Architekturregel

- Gemeinsam genutzte Geschäftslogik, Workflows und Datenmodelle bleiben
  sprachunabhängig. Domänen-/API-Antworten übermitteln stabile Codes,
  strukturierte Werte und lokalisierbare Parameter, nicht nur deutschsprachige
  Fehlermeldungen.
- Translation-Ressourcen sind versioniert, können ohne Änderung der
  fachlichen Freigabelogik gepflegt werden; pro Sprache gibt es nachvollziehbare
  Vollständigkeits-/Testberichte. Geeignete Formatierungsbibliothek und
  Frontend-Integration werden mit dem tatsächlichen Online-Stack entschieden
  (ICU-kompatible Plural-/Zahlen-/Datumsformatierung anstreben).
- Offline-Windows bleibt zunächst deutschsprachig. Eine künftig geteilte
  Schlüsselsystematik ist erwünscht, aber keine neue Online-Abhängigkeit darf
  die lokale Anwendung, Importprüfung oder Sicherheitssperren beeinträchtigen.

## Definition of Done für die erste mehrsprachige Online-Version

- DE/EN über durchgängige Benutzerreise von Projektanlage, Import,
  Verarbeitungsstatus, Fachprüfung, Berichtsvorschau und Export.
- Kritische Sperr-, Fehler- und Warnmeldungen sind vollständig übersetzt.
- Spracheinstellung funktioniert, Fallback ist getestet.
- Berichtssprache und freigegebene Dokumente sind revisionssicher.
- Testfälle bestehen für Sprachwechsel, Plural, Formate und Barrierefreiheit.
- Mindestens ein fachlich geprüfter Sprachtest pro initialer Zielsprache.

**Wichtig:** Diese Seite dokumentiert eine Produktanforderung. Sie behauptet
weder eine bereits verfügbare mehrsprachige Oberfläche noch eine abgeschlossene
Online-Entwicklung. Der aktuelle Pilot SC-0003 bleibt reine Offline-Testarbeit.
