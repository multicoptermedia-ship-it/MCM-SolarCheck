# SolarCheck Bedienungsanleitung

Status: Begleitdokument zur GUI-/UX-Definition. Diese Anleitung wird parallel zur
Oberfläche fortgeschrieben und vor Release gegen die implementierte Anwendung
verifiziert.

## 1. Grundprinzip

SolarCheck führt durch den Arbeitsablauf:

**Projekt anlegen -> Bilder importieren -> Verarbeitung -> Anlage prüfen ->
Befunde reviewen -> Bericht -> Export**

Online- und Offline-Version sollen dieselben Begriffe und denselben grundlegenden
Bedienablauf verwenden. Funktionen, die eine Internetverbindung benötigen, dürfen
die Offline-Auswertung nicht blockieren.

## 2. Neues Projekt anlegen

Auf dem Startbildschirm **Neues Projekt erstellen** wählen.

Zuerst Projekt- und Anlagendaten eintragen. Für den späteren Bericht sind
insbesondere vorgesehen:

- ausführende Firma mit Adresse und Kontaktdaten;
- verantwortliche Person;
- Anlagenname;
- Anlagenadresse;
- Anlagenbetreiber.

Optional können Ansprechpartner und Kontaktdaten des Anlagenbetreibers ergänzt
werden.

Das Projekt wird gespeichert, bevor Bilder importiert werden. Noch fehlende
Berichtsdaten bleiben als unvollständig gekennzeichnet und können später ergänzt
werden.

## 3. Bilder importieren

Nach dem Speichern **Bilder importieren** wählen. RGB- und Thermalbilder können
gemeinsam ausgewählt werden; eine vorherige Trennung durch den Nutzer ist nicht
erforderlich.

Je nach Plattform stehen Mehrfachauswahl, Ordnerauswahl und gegebenenfalls
Drag-and-drop zur Verfügung. Nach dem Import zeigt SolarCheck eine
Zusammenfassung der erkannten RGB-/Thermalbilder, Bildpaare und prüfbedürftigen
Dateien.

Aufnahmedatum, Aufnahmezeit und GPS-Informationen werden soweit möglich aus den
Bildmetadaten gewonnen und anschließend zur Kontrolle angezeigt. Fehlende oder
widersprüchliche Metadaten werden kenntlich gemacht und nicht erfunden.

## 4. Verarbeitung starten und überwachen

Wenn die Voraussetzungen erfüllt sind, **Verarbeitung starten** wählen.

SolarCheck zeigt den aktiven Verarbeitungsschritt und, sofern zuverlässig
messbar, Gesamtfortschritt, Prozentwert oder konkrete Bild-/Modulzähler. Ist für
einen Schritt kein belastbarer Prozentwert verfügbar, wird nur angezeigt, dass
die Verarbeitung läuft.

Bei einer Unterbrechung stehen abhängig vom tatsächlichen Backendzustand drei
unterschiedliche Wiederherstellungswege zur Verfügung:

- **Fortsetzen**: ab dem nächsten erforderlichen persistierten Verarbeitungspunkt;
- **Schritt erneut ausführen**: den betroffenen Schritt kontrolliert wiederholen;
- **Verarbeitung neu starten**: abgeleitete Verarbeitungsergebnisse bewusst neu
  aufbauen.

Ein unveränderter Prozentwert bedeutet nicht automatisch, dass die Verarbeitung
hängt. Wo verfügbar, nutzt SolarCheck zusätzlich einen Aktivitäts-/Heartbeat-
Nachweis.

Importierte Originaldaten und menschliche Reviewentscheidungen dürfen durch eine
Wiederherstellung nicht stillschweigend gelöscht werden.

## 5. Anlagenansicht

Nach der Verarbeitung zeigt SolarCheck die gesamte PV-Anlage als zentrale
Bildansicht. Die Ansicht kann verschoben und gezoomt werden. Eine Funktion führt
jederzeit zurück auf die Gesamtanlage.

Die Bildansicht besteht aus mehreren Ebenen:

1. optionale Satelliten-/Kartenansicht zur Orientierung;
2. RGB-Orthofoto;
3. Thermalebene;
4. Modul-, Befund- und Review-Overlays.

Die Hintergrundkarte ist optional. Ohne Internetverbindung oder verfügbare lokale
Karte wird sie einfach nicht angezeigt; die Auswertung funktioniert vollständig
weiter.

## 6. RGB und Thermal vergleichen

Zwischen **RGB**, **Thermal** und **Vergleich** kann gewechselt werden. Zoom und
Position bleiben beim Wechsel erhalten.

Im Vergleichsmodus wird am rechten Rand der Anlagenbildfläche ein Slider
angedeutet. Diesen von rechts nach links in das Bild ziehen, um RGB- und
Thermalansicht direkt miteinander zu vergleichen. Die Trennlinie kann danach in
beide Richtungen bewegt werden.

Der Slider ist eine visuelle Vergleichshilfe. Er stellt keine zusätzliche Aussage
über die Genauigkeit der Sensorregistrierung dar.

## 7. Module und Befunde

Ein Modul in der Anlagenansicht auswählen, um die kompakte Befundbox zu öffnen.
Dort werden je nach vorhandenen Daten Modulidentität, Reviewstatus, ein kurzer
Befundhinweis, relevante validierte Thermalwerte und ein Hinweis auf notwendigen
Review angezeigt.

Automatische Empfehlungen sind von einer menschlich bestätigten Bewertung zu
unterscheiden. Ausführlichere Informationen stehen über **Berichtdetails** bzw.
im späteren Bericht zur Verfügung.

## 8. Review / Prüfung

Die Reviewansicht kombiniert die Anlagenansicht mit einem vertikal scrollbaren
Befund-Stream. Standardmäßig stehen die tatsächlich prüfrelevanten Module im
Vordergrund, nicht sämtliche unauffälligen Module der Anlage.

Eine Befundkarte kann RGB-/Thermalausschnitt, Modulidentität, Kurzbefund,
Messwerte, automatische Empfehlung und Reviewstatus enthalten.

Soweit freigegeben stehen die Entscheidungen **Bestätigen**, **Unklar** und
**Verwerfen** zur Verfügung. Erst der persistierte Reviewzustand gilt als
maßgeblich.

Wird eine Befundkarte ausgewählt, hebt SolarCheck das zugehörige Modul in der
Anlagenansicht hervor. Wird ein Befund in der Anlagenansicht gewählt, springt der
Review-Stream zur entsprechenden Karte.

Filter ermöglichen die gezielte Anzeige von offenen, bestätigten, unklaren oder
verworfenen Befunden. Für schwierige Fälle steht ein **Fokusmodus** mit größerer
RGB-/Thermalansicht sowie Vorheriger-/Nächster-Navigation zur Verfügung.

## 9. Wichtige Hinweise

Die grafische Oberfläche zeigt nur Zustände als abgeschlossen an, die durch
persistierte Projektdaten belegt sind. Automatische Klassifikationen bleiben
Empfehlungen; die menschliche Reviewentscheidung ist maßgeblich.

Fehlende Bilder, Messwerte oder Metadaten werden nicht künstlich ergänzt. Eine
optionale Karten-/Satellitenansicht dient nur der Orientierung und ist keine
Inspektionsgrundlage.

## 10. Bericht und Export

Wenn Verarbeitung und erforderliche Prüfung abgeschlossen sind und die
Backend-Prüfungen dies bestätigen, stehen die Hauptaktionen **Bericht** und
**Export** zur Verfügung.

**Bericht** öffnet die ausführliche Berichtansicht mit den persistierten
Anlagen-/Betreiberdaten, Befunden, Belegen und Provenienzinformationen. Eine
Vorschau ist nicht automatisch mit einer Freigabe des Berichts gleichzusetzen.

**Export** öffnet die tatsächlich unterstützten Ausgabeformate. Ist Bericht oder
Export noch blockiert, bleibt die Funktion erkennbar und SolarCheck zeigt den
Grund, zum Beispiel eine noch offene Prüfung oder fehlende Pflichtangaben.

## 11. Menüleiste

Zusätzlich zu den Schaltflächen und der linken Arbeitsnavigation stehen die
Bedienfunktionen über bekannte Drop-down-Menüs im Kopf der Anwendung zur
Verfügung.

Vorgesehen sind **Projekt**, **Verarbeitung**, **Ansicht**, **Prüfung**,
**Bericht**, **Export** und **Hilfe**. Hierüber lassen sich dieselben zulässigen
Aktionen erreichen wie über die jeweilige Arbeitsansicht.

Ein Menüeintrag umgeht keine Sperre. Ist eine Funktion fachlich noch nicht
zulässig, bleibt sie nach Möglichkeit sichtbar, aber deaktiviert; ein Hinweis
erklärt den Grund.

Unter **Hilfe** ist diese Bedienungsanleitung erreichbar. Versionsinformationen
und spätere Diagnose-/Supportfunktionen können dort ebenfalls eingeordnet werden.

## 12. Noch zu ergänzende Kapitel

Konkrete Dialoge/Fehlermeldungen, Tastaturbedienung, Installation/Update der
Windows-Offline-Version sowie gegebenenfalls Online-Anmeldung/Synchronisierung
werden ergänzt, sobald die jeweiligen GUI- und Release-Verträge festgelegt sind.
