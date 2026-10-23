# SolarCheck – Operativer Masterplan und Projektstatus

Stand: 2026-10-04

Dieses Dokument ist die kanonische operative Statusreferenz im Repository. Es ersetzt die ältere Phasennummerierung für die laufende Entwicklung. Der tatsächlich implementierte Code und grüne CI-Gates bleiben maßgeblich.

## Arbeitsregel

Jeder Block folgt strikt:

**Code → gezielte Tests → Commit/Push → CI Python 3.11 + 3.12 grün → Status aktualisieren → nächster Block**

Ein neuer Funktionsblock beginnt nicht, solange das vorherige Gate rot oder ungeklärt ist. Fachliche Zustandsübergänge dürfen nicht durch GUI-, Provider- oder Test-Hilfskonstrukte umgangen werden.

## Gesamtstand

- Phasen 1–8: Kernfunktion, Analyse, Radiometrie sowie Projekt-/Workflow-Grundlagen – abgeschlossen.
- Phase 9: Online-Grundarchitektur/Vorbereitung – abgeschlossen.
- Phase 10A: Online Acceptance Profile – abgeschlossen.
- Phase 10B: provider-neutrale Compute Jobs – abgeschlossen.
- Phase 10C: Server Lifecycle, Ownership & Capacity – abgeschlossen.
- Phase 10D: Verified Identity & Registration – abgeschlossen und in den Online-Ablauf integriert.
- Phase 10E: Delivery & Billing Eligibility – abgeschlossen.
- Phase 10F: Payment Domain & Provider Abstraction – weit fortgeschritten.
- Phase 10G: Merchant Accounts & Secret Handling – weit fortgeschritten.
- Phase 10H: SEPA / PayPal / Card Infrastruktur – Architektur und Kernlogik vorhanden.
- Phase 10I: Voucher/Pricing System – Kernlogik und atomare Schutzmechanismen vorhanden.
- Phase 10J: Payment/Webhook/Crash Safety – abgeschlossen.
- Phase 10K: Persistence Migrations & Recovery Hardening – abgeschlossen.
- Phase 10L: End-to-End Online Payment Integration – abgeschlossen.
- Phase 10M: Operational Readiness / Deployment Gates – abgeschlossen.
- Phase 11: öffentlicher Produktbetrieb / Expansion – begonnen mit Produkttrennung und provider-neutraler Online-Persistence-Grenze.

## Phase 10L – abgeschlossen

Die End-to-End Online Payment Integration ist vollständig durch den vereinbarten Gesamtcheck gegangen.

- 10L.1: Registration- und Compute-Persistenz produktiv komponiert.
- 10L.2: Billing an autoritativ abgeschlossenen Compute Job gebunden.
- 10L.3: Delivery → Billing Release → Capture integriert.
- 10L.4: persistentes Pricing, Merchant Stores und Checkout komponiert.
- 10L.5: vollständiger Card-Lifecycle als E2E-Pfad.
- 10L.6: Registration Service produktiv komponiert und persistiert.
- 10L.7: verifiziertes Produkt-Entitlement persistent gemacht; Online-Compute-Erstellung erfordert aktives Entitlement.
- 10L.8: Checkout erfordert einen zum Job, Nutzer und Projekt passenden Billing-Kontext; ohne diesen Kontext wird kein Payment erzeugt.
- 10L.9: PayPal ist als vollständiger komponierter Authorize/Delivery-Release/Capture-Pfad verifiziert; Capture vor erfolgreicher Delivery bleibt gesperrt.
- 10L.10: SEPA ist als eigener asynchroner Pricing/Checkout → Delivery Release → Submission → Reconciliation-Pfad produktiv komponiert; Pricing- und Merchant-Snapshots bleiben erhalten.
- 10L.11: Fehlgeschlagene Reportzustellung lässt Report Retrieval und Billing Release aus und hält ein autorisiertes Payment unverändert; Capture bleibt gesperrt.

Gesamtcheck 10L: GitHub Actions Run #1582 auf PR #3 / Head `9e4f134`, Python 3.11 und 3.12 erfolgreich.

## Konsistente Online-Abfolge

Die serverseitig zu erhaltende Reihenfolge lautet:

**Registration → VERIFIED identity → active product entitlement → Compute Job → COMPLETED → Billing context → Pricing/Checkout → Payment authorization bzw. methodenspezifische Verarbeitung → Export → Report retrieval → Billing Release → Capture/Settlement**

Wichtig: Bei authorize/capture-fähigen Verfahren kann die Autorisierung vor der erfolgreichen Reportzustellung stattfinden. **Capture bzw. endgültige Zahlungsfreigabe darf jedoch nicht vor erfolgreicher Delivery und Billing Release erfolgen.**

Für SEPA gilt der eigene asynchrone Verarbeitungs- und Reconciliation-Pfad; er darf nicht künstlich in den Card/PayPal-Authorize/Capture-Ablauf gezwungen werden.

## Zentrale Sicherheitsinvarianten

- Kein Online-Compute-Job ohne aktives persistentes Produkt-Entitlement.
- Kein Billing-Kontext ohne abgeschlossenen, korrekt zugeordneten Compute Job.
- Kein Checkout ohne passenden Billing-Kontext.
- Billing erst nach Export und erfolgreichem Report-Abruf freigeben.
- Keine Abrechnung bei fehlgeschlagener Delivery.
- Billing Release atomar und einmalig.
- Höchstens ein Payment pro Compute Job.
- Provider- und Merchant-Snapshots bleiben am Payment gebunden.
- Provider-Secrets werden nicht im Payment oder in der Datenbank gespeichert; Auflösung nur an Resolver-/Adaptergrenzen.
- Providerwechsel für ein gebundenes Payment ist nicht zulässig.
- Capture und Void sind gegenseitig ausschließend.
- Provider-Operationen verwenden persistente Intents und stabile Idempotency Keys.
- Webhooks sind authentifiziert, replay-geschützt und dürfen terminale Zustände nicht zurücksetzen.
- Voucher-Einlösung und Payment-Erzeugung sind atomar; 100%-Voucher vermeiden unnötige Provider-Aufrufe.
- Persistierte Tarif-/Voucher-/Merchant-Snapshots schützen historische Payments vor späteren Konfigurationsänderungen.

## Phase 10M – Operational Readiness / Deployment Gates

10M behandelt ausschließlich Operational Readiness und Deployment Gates. Die in 10L verifizierten fachlichen Payment-/Delivery-Sequenzen bleiben dabei unverändert und dürfen nicht durch Deployment- oder Admin-Hilfslogik umgangen werden.

- 10M.1: Produktionsbereitschaft prüft fail-closed SMTP, Payment-/SEPA-Provider, einen aktuell wirksamen aktiven Tarif sowie aktive Merchant Accounts für Card, PayPal und SEPA. Verifiziert mit GitHub Actions Run #1588 auf Python 3.11 und 3.12.
- 10M.2: explizite fail-closed Online-Aktivierungsgrenze umgesetzt. Online startet INACTIVE und kann erst nach erfolgreichem Production-Readiness-Gate ACTIVE werden; ein fehlgeschlagener Aktivierungsversuch bleibt INACTIVE. Der Desktop-Einstieg bleibt getrennt. Verifiziert mit GitHub Actions Run #1592 auf Python 3.11 und 3.12.
- 10M.3: produktive Activation Boundary an die Online-Service-Komposition gebunden. Die Komposition stellt den Zustand von Beginn an explizit als INACTIVE bereit; erst der vollständige Readiness-Gate erlaubt die explizite Umschaltung auf ACTIVE. Der Offline-Einstieg und die fachlichen 10L-Sequenzen bleiben unverändert. Verifiziert mit GitHub Actions Run #1600 auf Python 3.11 und 3.12.
- 10M.4: deployment-aware Customer-Entry-Gate umgesetzt. Online-Kundeneintritt setzt den ACTIVE-Zustand voraus; Offline Desktop bleibt unabhängig von Online-Production-Readiness. Da noch kein produktiver Web/API-Server-Entrypoint im Repository existiert, wurde kein fiktiver Server verdrahtet; künftige reale Online-Entrypoints müssen diese Service-Grenze verwenden. Verifiziert mit GitHub Actions Run #1604 auf Python 3.11 und 3.12.
- Gesamtcheck 10M: PR #3 zeigt auf den verifizierten Head `82a2bc5`, ist offen und mergeable; GitHub Actions Run #1604 ist auf Python 3.11 und 3.12 erfolgreich. Die 10L Payment-/Delivery-Sequenzen und der Offline-Desktop-Einstieg bleiben unverändert.

## Phase 11 – Public Product Operation / Expansion

Phase 11 ist nach abgeschlossenem 10M-Gate begonnen. Online und Offline besitzen getrennte Produkt- und Kompositionsgrenzen, teilen aber weiterhin denselben fachlichen SolarCheck-Core. Die bestehenden Readiness-, Activation-, Customer-Entry- und 10L-Fachgates bleiben verbindlich.

### Provider-neutrale Online-Persistence – Meilenstein abgeschlossen

Der zentrale `OnlinePersistence`-Container ist vollständig über Service-/Domain-Ports typisiert; der zuvor verwendete Übergangstyp `Any` ist entfernt. Der aktuelle Builder verwendet weiterhin die vorhandenen SQLite- und privaten Filesystem-Adapter, ohne diese konkreten Typen in den zentralen Persistence-Vertrag zu tragen.

Provider-neutral abgegrenzt sind Registration, Entitlements, Compute Jobs, Billing, Payments, Merchant Accounts, Tarife, Voucher und atomare Pricing-Persistenz, Payment Operation/Authorization Intents, SEPA Mandate/Submission/Collection, Invoice Identity/Delivery/Archive, Report Artifact/Recovery sowie SMTP Settings/Secrets/Audit.

Dabei bleiben insbesondere erhalten:

- Payment-Operation- und Authorization-Intents mit persistenter Crash-Recovery-Sequenz `RESERVED → PROVIDER_SUCCEEDED → COMPLETED` und stabilen Idempotency Keys.
- Capture/Void bleiben gegenseitig ausschließend; Provider-Erfolg wird vor lokalem Abschluss dauerhaft belegt.
- SEPA bleibt ein eigener asynchroner Mandate → Submission → Collection/Reconciliation-Pfad mit Lease-/Idempotency- und Event-Ordering-Schutz.
- Voucher-Einlösung und Payment-Erzeugung bleiben atomar; Tarif-, Voucher-, Merchant- und Provider-Snapshots bleiben historisch reproduzierbar.
- Report Retrieval/Delivery und Billing Release bleiben Voraussetzung für die nachgelagerte Rechnungsfreigabe.
- SMTP-Secrets bleiben von nicht-geheimer Konfiguration und secret-freiem Admin-Audit getrennt.

Verifiziert mit GitHub Actions Run #1640 auf Python 3.11 und 3.12. Der produktive MySQL-8.0-Adapter ist damit weiterhin ein späterer eigener Implementierungs-/Migrationsblock; dieser Meilenstein führt noch keinen MySQL-Treiber und keine MySQL-spezifische SQL-Logik ein.

### Produkttrennung und Online-Login/Verification – aktueller Stand

Die Produktgrenzen sind inzwischen auch in den ausführbaren Einstiegspfaden konkretisiert. Offline und Online bleiben physisch getrennt, während der gemeinsame SolarCheck-Projektworkflow im gemeinsamen Core verbleibt.

- Offline: Der Desktop-Einstieg läuft über die explizite Offline-Produktkomposition. Commit `3334ab5`, GitHub Actions Run #1644, Python 3.11 und 3.12 erfolgreich.
- Online: Der Shell-Workflow ist an den Customer-Entry-Gate gebunden. Commit `9f3b405`, Run #1646, Python 3.11 und 3.12 erfolgreich.
- Online: Das Fenster wird über die explizite OnlineProduct-Komposition aufgebaut. Commit `6993235`, Run #1648, Python 3.11 und 3.12 erfolgreich.
- Online-Login: Registrierungsfelder und E-Mail-Verifikation sind im Anmeldefenster sichtbar, ohne VERIFIED- oder Entitlement-Status in Qt zu erzeugen. Commit `04b388f`, Run #1650, Python 3.11 und 3.12 erfolgreich.
- Online-Login: Registrierung und Token werden über eine UI-seitige Controller-Grenze geleitet. Nach zwei ausschließlich testseitigen Reparaturen (`3247a38`, `ba3e1d0`) war Run #1656 auf Python 3.11 und 3.12 erfolgreich.
- Online-Login: Der Controller delegiert Registrierung und Verifikation an den vorhandenen `OnlineRegistrationService`; UTC-Zeit und Produktpolitik bleiben außerhalb der GUI. Commit `be4b92c`, Run #1658, Python 3.11 und 3.12 erfolgreich.
- Online-Komposition: `build_online_window()` erzeugt den Registration-Controller aus dem komponierten Registration-Service; die aktuelle Verifikation aktiviert dabei das fest konfigurierte TRIAL-Entitlement. Commit `ea7b276`, Run #1660, Python 3.11 und 3.12 erfolgreich.
- Online-Login: Erfolg und fachliche Validierungs-/Tokenfehler werden im Anmeldefenster sichtbar zurückgemeldet; die GUI entscheidet weiterhin nicht über VERIFIED oder Entitlement. Commit `ccef6d6`, Run #1662, Python 3.11 und 3.12 erfolgreich.
- Online-Entry: Der Customer-Entry-Gate kann einen identifizierten Benutzerkontext verlangen und prüft dann zusätzlich zur aktiven Production-Freigabe das persistierte aktive Entitlement. Commit `0e140b5`, testseitig korrigiert mit `be7793a`; Run #1668 auf Python 3.11 und 3.12 erfolgreich.
- Online-Verification: Der Registration-Controller übernimmt die Benutzer-ID ausschließlich aus dem vom serverseitigen Verification-Service zurückgegebenen aktiven Entitlement; vor erfolgreicher Verifikation existiert kein verifizierter Benutzerkontext. Commit `720030e`, Test-Double an die bestehende Service-Rückgabe angepasst mit `9db3187`; Run #1672 auf Python 3.11 und 3.12 erfolgreich.
- Online-Workflow-Eintritt: Nach erfolgreicher Token-Verifikation wird die bestätigte Benutzer-ID an den Customer-Entry-Gate übergeben. Erst wenn Production ACTIVE und das persistierte Entitlement für genau diesen Benutzer bestätigt sind, wechselt die Shell auf die Projektseite; Fehler verbleiben fail-closed auf Login. Commit `e5686eb`, Run #1674 auf Python 3.11 und 3.12 erfolgreich.
- Online-Verification HTTP: Eine transportneutrale HTTP-Grenze delegiert `/verify-email?token=…` an den autoritativen Registration-Service; ungültige oder abgelaufene Token bleiben fail-closed. Commit `45b4568`, Run #1678 auf Python 3.11 und 3.12 erfolgreich.
- Online-Verification HTTP: Ein Standardbibliothek-Adapter stellt den lokalen/testbaren GET-Pfad bereit, ohne einen zusätzlichen Web-Framework-Stack einzuführen oder den Server-Lifecycle zu übernehmen. Commit `f5bdd77`, Run #1680 auf Python 3.11 und 3.12 erfolgreich.
- Online-Verification Integration: Der HTTP-Adapter wird aus der bestehenden `OnlineProduct`-/Registration-Komposition aufgebaut. Der Integrationstest belegt Registrierung → Bestätigungslink → HTTP-Verifikation → VERIFIED → persistiertes aktives TRIAL-Entitlement. Commit `f4b608b`, Testimport korrigiert mit `54b6f19`; Run #1684 auf Python 3.11 und 3.12 erfolgreich.

- Öffentlicher Online-Einstieg: Der lokale/testbare HTTP-Adapter stellt die Kundenstartseite sowie POST `/register` bereit; Registrierung wird ausschließlich an den Registration-Service delegiert. Die Transportgrenze ist gegen falschen Content-Type, unvollständige/mehrdeutige Felder und übergroße Bodies fail-closed gehärtet. Commits `5066396`, `609c5bf`, `fd7e549`; bis Run #1694 auf Python 3.11 und 3.12 erfolgreich.
- Authentifizierung: Eine provider-neutrale Authentication-Grenze akzeptiert nur bereits VERIFIED registrierte Identitäten. Passwort-Credentials werden als gesalzene PBKDF2-HMAC-SHA256-Ableitungen gespeichert; Klartextpasswörter werden nicht persistiert. SQLite ist der aktuelle Dev/Test-Adapter hinter dem neutralen CredentialStore. Commits `cf1a806`, `9ac2e4a`, `e2b3a45`; bis Run #1700 grün.
- Login-Komposition: Credential-Proof wird vor der VERIFIED-Identity-Prüfung ausgeführt; externe Login-Fehler bleiben generisch. POST `/login` bildet diese Service-Sequenz auf HTTP ab. Commits `277ee3f`, `0828e96`; Run #1710 grün.
- Registrierungs-Credentials: Online-Registrierung verlangt ein Passwort, hält es außerhalb des Registration-Service und validiert die zentrale Passwort-Policy jetzt **vor** Registration-/E-Mail-Nebenwirkungen. Erst nach erfolgreicher Vorprüfung wird registriert und anschließend das Credential persistiert. Reparatur-/Kompositionsfolge `adfab79` → `3a52734` → `2ba70f3`; Sequenzhärtung `02165e3`, Run #1722 auf Python 3.11 und 3.12 erfolgreich.
- Server-Sessions: Erfolgreicher Login erzeugt einen opaken serverseitigen Session-Token. Das Browser-Cookie enthält keine Benutzer-ID und kein Passwort; es ist HttpOnly und SameSite=Strict, mit explizit aktivierbarem Secure-Flag für HTTPS-Deployment. Commit `8eb66ca` (Session-Grenze), `9e064eb` (Login→Cookie); bis Run #1714 grün.
- Geschützter Kundeneinstieg: GET `/customer-entry` übernimmt die Benutzer-ID ausschließlich aus der serverseitig aufgelösten Session und führt danach Production-Aktivierung plus persistiertes Benutzer-Entitlement über den bestehenden Customer-Entry-Gate aus. Fehlende/ungültige Session wird als 401, fehlende fachliche Freigabe als 403 behandelt. Commit `0537e5a`, Run #1716 grün.
- Session-Persistenz: Der provider-neutrale SessionStore besitzt einen SQLite-Adapter im OnlinePersistence-Container; gültige Sessions überleben damit Service-/Server-Rekomposition. Ablauf und Revoke werden dauerhaft wirksam. Commit `abdfce6`, Run #1718 grün. Ein späterer MySQL-8.0-Adapter ersetzt nur diese Infrastrukturgrenze, nicht die Session-/Auth-Servicefolge.
- Logout: POST `/logout` widerruft eine vorhandene serverseitige Session und löscht das Browser-Cookie per Max-Age=0; wiederholter Logout ohne Session bleibt idempotent erfolgreich. Commit `eb4b817`, Run #1720 grün.
- Session-Sicherheit: Persistierte Bearer-Session-Tokens werden im SQLite-Adapter nur als SHA-256-Fingerprints gespeichert; der rohe Token bleibt ausschließlich beim Client/Service-Aufruf. Commit `4a43189`, Run #1726 auf Python 3.11 und 3.12 erfolgreich.
- Session-Lebensdauer: Das Browser-Cookie erhält ein `Max-Age`, das aus dem serverseitigen Session-Ablauf abgeleitet wird; eine bereits abgelaufene neu erzeugte Session wird widerrufen und nicht als Cookie ausgegeben. Commit `e2dbc61`, Run #1728 auf Python 3.11 und 3.12 erfolgreich.
- Produktions-HTTP: Produktionskomposition verlangt explizit Secure-Cookies; `production=True` ohne `secure_cookies=True` wird fail-closed abgewiesen. Lokale Plain-HTTP-Tests bleiben davon getrennt. Commit `4c09570`, Run #1730 auf Python 3.11 und 3.12 erfolgreich.
- Persistierte Session-Zeitwerte: malformed, timezone-naive oder nicht-UTC gespeicherte Ablaufzeitpunkte werden nicht als gültige Session akzeptiert. Commit `e93b6bb`, Run #1732 auf Python 3.11 und 3.12 erfolgreich.
- Report-Zeitzonen: Projektprofile können eine explizite IANA-Zeitzone wie `Europe/Berlin` persistieren. Interne/Quellzeitpunkte bleiben timezone-aware; beim Report-Assembly wird der Prüfzeitpunkt in die Projektzeitzone umgerechnet, sodass Sommer-/Winterzeit über `zoneinfo` korrekt berücksichtigt wird. Bestehende Projekte ohne Zeitzone erhalten keine erfundene Länderzuordnung. Schema v14 und Report-Konvertierung wurden mit `a288614` eingeführt; Migrationstests mit `61473cc` an den vollständigen v14-Pfad angepasst. Run #1736 ist auf Python 3.11 und 3.12 erfolgreich.
- Report-Zeitzonen-Härtung: Der Report-Assembler akzeptiert den technischen Prüfzeitpunkt nur als timezone-aware UTC und konvertiert erst an der Report-Grenze in die explizit gespeicherte IANA-Standortzeitzone. PDF, DOCX und ODT verwenden eine gemeinsame Darstellung mit lokaler Zeit, Zonenname und UTC-Offset. Neue Projekte erfassen die Standortzeitzone als validierte Stammdaten; Projekt und Profil werden atomar angelegt. Migrierte Altprojekte ohne Zeitzone bleiben als Draft bearbeitbar, ein `released`-Report wird jedoch fail-closed bereits am Application Service vor möglichen Asset-Schreibvorgängen und zusätzlich im Assembler blockiert. Umgesetzt in `e56c929`, `55caa80`, `02ba1e4`, `933ae9b`, `0daf542`, `ef30fdf`, `15a8ddf`, `1912d94`, Test-Fixture-Reparatur `a49ad8a` und Application-Gate `a608308`; letzter bestätigter Gate-Run #1758 auf Python 3.11 und 3.12 erfolgreich.


### Online-Projektworkflow – persistente Kundenintegration

Der gemeinsame SolarCheck-Projektworkflow ist jetzt auch über die Online-Produktkomposition an den persistenten Online-Zustand angebunden:

- Online-Projekte und Projektprofile verwenden dieselbe private State-SQLite-Datenbank wie die übrigen aktuellen Online-Dev/Test-Stores; es entsteht keine zweite Projekt-Datenbank. Commit `5951f7c`, Testkorrektur `de8821a`; Run #1764 auf Python 3.11 und 3.12 erfolgreich.
- `OnlineServices` komponiert den `ProjectApplicationService` aus dieser autoritativen Persistence. Commit `8eff054`; Run #1766 auf Python 3.11 und 3.12 erfolgreich.
- Der normale Online-Desktop-Shell-Pfad verwendet standardmäßig den komponierten Projektservice statt einer separaten externen Projektzustands-Injektion. Commit `46c4be5`; Run #1768 auf Python 3.11 und 3.12 erfolgreich.
- Nach verifiziertem Kundeneinstieg bleibt die bestätigte Benutzer-ID an die laufende Online-Shell gebunden. Weitere Online-Navigation prüft Production und persistiertes Entitlement erneut mit genau dieser Identität; Navigation ohne verifizierte Identität bleibt fail-closed. Commit `cc19ff8`, Testanpassungen `b2c0f4b` und `7b86e64`; Run #1774 auf Python 3.11 und 3.12 erfolgreich.
- Ein Integrationstest belegt, dass ein über `OnlineServices.projects` angelegtes Projekt inklusive Projektprofil und expliziter IANA-Zeitzone `Europe/Berlin` nach vollständiger Persistence-/Service-Rekomposition aus derselben privaten State-Datenbank wieder geladen wird. Commit `e9b863d`; Run #1776 auf Python 3.11 und 3.12 erfolgreich.

Damit ist für den aktuellen SQLite-basierten Online-Dev/Test-Adapter die Kette **verifizierter Kundeneinstieg → identitätsgebundene Online-Shell → persistente Projektanlage/-auswahl → gemeinsamer SolarCheck-Projektworkflow** geschlossen. Der spätere MySQL-8.0-Adapter bleibt ein eigener Infrastruktur-/Deployment-Block und darf diesen fachlichen Ablauf nicht verändern.

Die aktuell implementierte Eintrittssequenz lautet damit:

**Website/Kundeneinstieg → OnlineProduct / OnlineServices → Registrierung mit vorgelagerter Passwortvalidierung → Bestätigungs-E-Mail → /verify-email?token=… → serverseitige Token-Verifikation → VERIFIED identity + aktives TRIAL-Entitlement → POST /login (Credential-Proof → VERIFIED-Identity-Prüfung) → persistente serverseitige Session + Browser-Cookie → GET /customer-entry → Customer-Entry-Gate (Production ACTIVE + persistiertes Benutzer-Entitlement) → Projektseite → gemeinsamer SolarCheck-Projektworkflow → POST /logout / Session-Revoke**

Der lokale/testbare HTTP-Pfad für Startseite, Registrierung, Verifikation, Login, Session, geschützten Kundeneinstieg und Logout ist implementiert. Persistierte Session-Tokens werden nur als Fingerprints gespeichert, Cookie-Lebensdauer und serverseitiger Ablauf sind gekoppelt, und ungültige persistierte Ablaufzeitpunkte werden fail-closed behandelt. Für Produktions-HTTP sind Secure-Cookies verpflichtend; der lokale Plain-HTTP-Testadapter bleibt davon getrennt. Ein produktiver öffentlicher Webserver-/Deployment-Adapter für IONOS sowie der geplante MySQL-8.0-Infrastrukturadapter bleiben eigene spätere Gates und dürfen diese verifizierte Auth-/Entitlement-/Customer-Entry-Sequenz nicht verändern. Die manuelle Token-Eingabe im Desktop-Login bleibt bis zur vollständigen Webintegration als Fallback-Grenze erhalten.

### Produktstrategie für Phase 11

- **SolarCheck Online ist das primäre Kundenprodukt.** Die öffentliche Website `mcm-solarcheck.de` soll Kunden später ausschließlich in den Online-Einstieg führen; Registrierung, E-Mail-Verifikation, Entitlement und Production-Gate bleiben dabei verbindlich.
- **SolarCheck Offline bleibt vorerst eine interne MCM-Arbeits- und Testversion.** Sie wird aktuell nicht öffentlich auf der Website angeboten und erhält keinen öffentlichen Downloadpfad.
- Die Offline-Version dient der ausführlichen praktischen Erprobung des gemeinsamen SolarCheck-Cores. Eine spätere Vermarktung der Offline-Version ist eine gesonderte Produkt-/Release-Entscheidung nach ausreichenden Praxistests.
- Die öffentliche Website darf Online- und Offline-Einstieg nicht vermischen. Ein späterer Offline-Installer, Lizenzierung, Update-Mechanismus, Preis und Download werden erst in einem eigenen Freigabeblock behandelt.

## Spätere Produkt- und Release-Arbeitsströme

Nach der Online-Betriebsreife bleiben insbesondere erhalten:

- konkrete GUI-/Admin-Implementierung,
- Admin-Pricing mit manuell pflegbaren Leistungsstufen und versionierten Preisen gemäß [admin-product-requirements.md](admin-product-requirements.md),
- Offline-Desktop-Version auf demselben fachlichen Domain-Core,
- Windows-Offline-Installer,
- wissenschaftliche Modellvalidierung,
- gesonderte Prüfung gegen DIN IEC/TS 62446-3 und interne Vorgaben,
- konkrete Pricing-/Pilotkostenentscheidung,
- optionaler Flugplaner,
- abschließende E2E-, Release- und Praxistests.

## Datenbankstrategie Online / Offline

- Offline Desktop bleibt lokal und verwendet SQLite; die Offline-Version darf keine produktive Online-Datenbank voraussetzen.
- SolarCheck Online erhält eine austauschbare Persistence-Grenze. SQLite bleibt für Entwicklung und automatisierte Tests nutzbar.
- Für den späteren produktiven IONOS-Betrieb ist ein MySQL-8.0-Adapter vorgesehen, sofern der konkrete IONOS-Tarif zum Deployment-Zeitpunkt MySQL 8.0 bereitstellt.
- Domain-, Workflow-, Review-, Reporting-, Billing- und Payment-Logik dürfen nicht an SQLite- oder MySQL-spezifisches SQL gekoppelt werden.
- SQLite-spezifische Konstrukte wie PRAGMA, BEGIN IMMEDIATE und Platzhaltersyntax bleiben auf Infrastrukturadapter begrenzt und werden nicht in den gemeinsamen Core übernommen.
- Datenbank-Hostname, Port, Datenbankname und Benutzername sind Deployment-Konfiguration; Passwörter und weitere Zugangsdaten sind Secrets und werden weder im Repository noch in fachlichen Persistenzobjekten gespeichert.
- Eine spätere SQLite→MySQL-Migration wird als eigener getesteter Deployment-/Persistence-Block durchgeführt. Sie darf die verifizierten Online-Fachsequenzen nicht verändern.

## Architekturprinzip Online / Offline

Online und Offline teilen ab dem eigentlichen SolarCheck-Projektworkflow denselben fachlichen Domain-Core. Online ergänzt Identität, Entitlement, serverseitige Compute-/Delivery-/Billing-/Payment-Orchestrierung. Offline darf diese Online-spezifischen Zugangsschichten nicht benötigen, muss aber dieselben fachlichen Review-, Provenienz- und Report-Gates respektieren.

Zeitinvariante für Berichte: technische Persistenz und Verarbeitung verwenden timezone-aware Zeitpunkte; UTC bleibt die kanonische interne Referenz. Kunden-/Prüfberichte geben Auswertungs- und Prüfzeiten in der explizit gespeicherten IANA-Zeitzone des jeweiligen Projektstandorts aus. Es werden weder feste UTC-Offsets noch allein aus Ortsnamen oder Ländern geratene Zeitzonen verwendet; Sommer-/Winterzeit muss durch die Zeitzonendaten korrekt abgebildet werden. Bestehende Projekte ohne bekannte Standort-Zeitzone bleiben explizit unvollständig, bis die Zeitzone erfasst ist.

Die menschliche Fachprüfung bleibt maßgeblich. Fehlende Evidenz darf nicht künstlich erzeugt werden. Unklare Freigabezustände werden fail-closed behandelt. Technische Softwarefreigabe, wissenschaftliche Modellvalidierung, Normprüfung und kommerzielle Produktfreigabe bleiben getrennte Gates.

## Statusfortschreibung 22. Oktober 2026 – Integrationslücke vor Phase A

Diese Aktualisierung hat Vorrang vor der älteren pauschalen Phasenübersicht,
ohne die historischen Abläufe 1–11 oder die getrennte Online-Roadmap
rückwirkend umzubenennen. Für die aktuell zu pilotierende **Windows-10-
Offline-Inspektionssoftware** ist entscheidend, was wirklich
durchgehend funktioniert und was noch Fachabnahme braucht.

### Jetzt verbunden: DJI M3T Original-ZIPs → bestehendes lokales Projekt

- Der bisherige synchrone `ProjectApplicationService.import_project_images`
  legte beim Import in ein **bereits existierendes** Projekt erneut
  dieselbe Projektkennung an; er wird nun über denselben
  `import_project_images_cancellable`-Dienst und dessen atomare
  SQLite-Transaktion wie der bewährte Hintergrundimport geführt.
- Neu: `import_project_original_zips_cancellable` prüft ausdrücklich
  ausgewählte Thermal-/RGB-Original-ZIPs, sichert unveränderte
  Dateien in einer **privaten, dauerhaften und nur lokal vorhandenen**
  Ablage neben der Offline-Datenbank und übergibt deren Ordner
  an den bestehenden geschützten Import. Dadurch sind
  Bildreferenzen nach der Transaktion nicht auf einen gelöschten
  temporären Ordner gerichtet. Bereits importierte Projekte werden
  nicht versehentlich mit neuen ZIP-Inhalten überlagert.
- Der Staging-Prozess ist kooperativ abbrechbar. Bei fehlgeschlagener
  Validierung, Datenbankfehler oder Abbruch vor Commit werden
  ausschließlich die neu angelegten Kopien dieses Versuchs entfernt.
  Die Original-ZIPs, andere Projekte und bestehende Prüfentscheidungen
  werden nicht gelöscht. Keine Cloud, kein Trainingsstart.
- Die Offline-GUI hat eine eigene Bedienoption
  **„DJI-Original-ZIPs (Thermal + RGB) auswählen“**.
  Sie nutzt den vorhandenen QThread/Projektimport-Status und
  verlangt Thermal- und RGB-ZIP manuell. Der zusätzliche Import
  ungepaarter Thermalbilder ist standardmäßig **abgewählt**.
- Synthetische Integrationstests prüfen sichere Ablage, rückverfolgbare
  Quellen, sichtbare Bildpaarzahlen, Abbruch, fehlerhafte ZIPs,
  Schutz bestehender Projekte und UI-Auswahl. Ein nativer
  **Windows-10-Praxistest** mit 160/33 Originalbildern ist
  weiterhin offen; GitHub Windows CI läuft auf Server 2022.
- Das schließt **eine konkrete Projektimport-Integrationslücke**.
  Es ersetzt keine vollständige Anlagenanalyse. Weder Bildnummer
  noch Aufnahmedatum belegen pixelgenaue Sensorregistrierung.
  Die radiometrische APP3-Struktur ist verfügbar, aber
  produktive °C-Werte bleiben an die unabhängige DJI-
  Referenzvalidierung gebunden.

### Verbindliche Reihenfolge der weiteren Offline-Reife

1. **Integrationslücken und Phase A:** Den gesamten Ablauf auf einem
   realen Windows-10-Rechner mit privatem lokalem Testprojekt
   beobachten. Alle noch fehlenden Bedienübergänge und
   nichtpersistierten Zwischenresultate dokumentieren und
   gezielt schließen.
2. **Phase B:** Stabile Modulgeometrie, eindeutige Modulnummern,
   RGB/Thermal-Registrierung, Orthofoto bzw. fachlich validierter
   externer GIS-Fallback an der realen 600-kWp-Anlage abnehmen.
3. **Phase C:** Bestehende DJI-M3T-APP3/APP4/APP5-Forschung
   wiederverwenden; eine autoritative °C-Referenzvergleichs-
   und Temperaturprovenienzprüfung abschließen; beobachtbare
   Anomalie von nur vermuteter elektrischer Ursache trennen.
4. **Phase D:** Lizenzgeprüfte OSS-Daten, Standort-/Modul-
   disjunkte Testgruppen, menschlich überprüfte Fehlerlabels
   und reale Open-Source-Modelloptimierung; kein automatisches
   Deploy eines unvalidierten Modells.
5. **Phase E:** Fachkundige Freigabe, tatsächliche Bildbelege,
   prüfbares Modul/Anlagenlayout, Bericht als PDF/ODT/DOCX
   mit Pilotanwender abnehmen; keine PDF-Vorschau als Lesebestätigung.
6. **Phase F:** Echte Windows-10-End-to-End-Abnahme, reproduzierbare
   offline installierbare Laufzeit samt Wheelhouse/Lizenzen,
   Datensicherung, Backups, Updates und signierten EXE-Installer
   auf gesonderter späterer Release-Schiene.

**Stoppregel:** Kein Block wird als produktiv fertig bezeichnet,
nur weil beide CI-Testmatrizen grün sind. Release, fachliche
Temperaturvalidierung, Kundenrechte und Modellvalidierung sind
eigenständige Gates. An `main` und PR #3/#4 nichts verändern,
bevor eine gesonderte Integrationsfreigabe vorliegt.

## Statusfortschreibung 22. Oktober 2026 – Windows-10-Abnahmehilfen (noch keine Fachabnahme)

- Ein opt-in, ausschließlich schreibgeschützter Vor-/Nachprüfer für den realen
  160/33-DJI-Original-ZIP-Import ist auf dem Offline-Featurebranch vorbereitet.
  Vorprüfung: ZIP-DJI-Identität und 33 Metadatenpaare; Nachprüfung: bestehendes
  Testprojekt und dessen SQLite-Framereferenzen im Read-only-Modus, private
  Provenienz und SHA-256-Originalvergleich. Fehlende Analysepaare werden nicht
  zu vollständiger Registrierung umgedeutet.
- Ausführung: `scripts/check_windows10_original_zips.ps1` auf **echtem
  Windows 10**, vor und nach dem ausdrücklich über die GUI gestarteten Import.
  Kein automatischer Import oder Zugriff auf alte Kundenprojekte.
- Die sechs lokalen/CI-Testarten bleiben von der echten Abnahme getrennt:
  Erst die 160/33-Originalbilder, ein frisches Offline-Testprojekt, der
  UI-Durchlauf, SQLite-Read-only-Nachweis und Neustart auf Windows 10
  können Phase A weiter freigeben. Test- und CI-Ergebnisse des neuen Blocks
  müssen nach dessen fünftem Commit gesondert bestätigt werden.

## Vorrangige Importentscheidung 22.10.2026 – Originaldateien statt ZIP-Pflicht

Der normale Anwender importiert **unverpackte DJI-M3T-Originaldateien** direkt
über **„DJI-Originaldateien auswählen (ohne ZIP)“** oder verwendet den bisherigen
**Bildordnerimport**. Vorherige Dokumentationsformulierungen, die ZIP als
Regelfall erscheinen lassen, sind historische Test-/Transferbeschreibung.
Die privaten ZIPs entstanden für den komprimierten Datentransfer an die
Entwicklung und sind **kein Produktzwang**.

Die neue Mehrfachdateiauswahl übergibt genau die gewählten Originale an den
vorhandenen QThread, validiert DJI-Dateiname, Sensorformat, EXIF-Kamera und
Aufnahmezeit sowie doppelte Identitäten, erstellt unveränderte private Kopien
mit SHA-256-Provenienz und benutzt dann **denselben atomaren
`ProjectApplicationService.import_project_images_cancellable`** zum
Speichern. Ohne vorherige ZIP-Erstellung und ohne zweite Projektdatenbank.
Ausdrücklich angewählte reine Thermaldateien werden mitgenommen und
nicht in scheinbare RGB/Thermal-Paare umgerechnet. Fehlende Paare
bleiben ersichtlich; Bildzähler-Zuordnung ist noch keine
pixelgenaue Registrierung. Dateikopie/Fehler/Abbruch vor SQLite-Commit
hinterlassen keine neue fachliche Projektpersistenz. Der etablierte
Ordnerimport wird nicht deaktiviert; sein Verhalten wurde in diesem
Block nicht stillschweigend umgeschrieben.

Die ZIP-Auswahl existiert nur noch als **optionale Sonderfunktion** für
bereits archivierte/übertragene Originale. Der ältere
Windows-10-Original-**ZIP**-Vor-/Nachprüfer ist entsprechend **nur**
für diese Sonderprüfung gedacht; er ist kein notwendiger Schritt
beim normalen Dateien- oder Ordnerimport.

**Abnahme noch ausstehend:** Das reale Windows-10-Gerät mit 160 originalen
Thermaldateien + 33 RGB-Dateien, reale EXIF-/MPO-Kompatibilität,
persistierte Mengen/Quellreferenzen, Abbruchfall, GUI-Neustart und
Bedienprüfung. Keine Aussage zu kalibrierten °C, physischer Modul-ID,
kundentauglichem Bericht, KI-Training oder allgemeiner Freigabe.


## Stand 22.10.2026 – Read-only Windows-10-Abnahme für normale DJI-Originaldateien

Der Standardimport **benötigt keine ZIP-Archive**. Neu ist eine gezielt
aufrufbare, schreibgeschützte technische Vor-/Nachprüfung der explizit
ausgewählten Original-JPG-/MPO-Dateien: `scripts/check_windows10_original_files.ps1`.
Der Anwender kann ein oder mehrere Verzeichnisse mit unverpackten DJI-Bildern
angeben, alternativ einzelne Dateipfade. Es erfolgt **keine automatische
Dateiübernahme durch das Prüftool** und keine Datenbankmigration.

Die neue Prüfung verwendet die gleichen DJI-Dateinamen-, EXIF-, Zeit-,
Kamera- und Bildgrößenbedingungen wie der eigentliche sichere Originaldatei-
Staging-Service. Nichtkanonische Schreibweisen werden derzeit ausdrücklich
abgewiesen, statt Dateien stillschweigend aus dem vorhandenen Importer
auszulassen. Quelle und private Kopie werden nach dem bewussten GUI-Import
per SHA-256 mit den gespeicherten Provenienzangaben abgeglichen. SQLite
wird mit `mode=ro` und `query_only` geöffnet. Die Ausgabe enthält nur
zusammengefasste Zahlen, keine Pfade, GPS, Dateinamen oder Hashwerte.

Die **33 Metadatenpaare** werden explizit von den **persistierten
Analyse-Paaren** unterschieden: Eine kleinere Zahl an Analysepaaren zeigt
`analysis_pair_review_required: true` und bleibt Fachprüfbedarf.
Importkontrolle bedeutet weiterhin **nicht** validierte RGB/Thermal-
Geometrie, absolute °C, physische Modul-ID oder fertigen PV-Bericht.

Für reale Abnahme weiterhin offen: Python-Laufzeit/Windows-10-Hardware,
alle 160 Thermal-/33 RGB-Originalbilder, echter MPO-/APP3-Import über die GUI,
geschütztes neues Testprojekt, Nachkontrolle, App-Neustart, stichprobenhafte
Bild-/Reviewanzeige, Abbruchfall und lokaler Backup-/Recovery-Nachweis.
CI nutzt ausschließlich synthetische DJI-Testbilder und Windows Server 2022.



## Phase-B-Vorbereitung 22.10.2026 – lokale Anlagenübersicht mit transparentem ID-Status

Die bestehende Anlagenübersicht zeigt bereits aus SQLite gelesene,
projektbezogene Modulbeobachtungen, Befunde und getrennte Review-Status.
Dieser neue, **bewusst rein lesende** Vertikalblock macht nun den
Fortschritt der algorithmischen Modul-ID-Zuordnung sichtbar:

- `InspectionQueries.module_identity_readiness(project_id)` zählt
  **alle** vorhandenen Modulbeobachtungen unabhängig von der gewählten
  UI-Seite (bis 100 Beobachtungen pro Seite), beobachtungsbezogene
  `new`/`matched`-Vorschläge mit tatsächlicher ID, offene
  Beobachtungen ohne passenden Vorschlag und unterschiedliche
  Vorschlagskennungen. Diese Kennungen sind **keine gezählten,
  validierten physischen PV-Module**.
- Nicht zu einer gespeicherten Modulbeobachtung passende
  `module_identity_links` werden als Datenkonsistenz-Warnung
  gezählt; sie werden weder gelöscht noch als Modul mitgerechnet.
- `ProjectApplicationService.plant_overview` bindet die
  projektweiten Zähler in dieselbe bestehende UI-Datenquelle ein;
  `gui/plant_overview_page.py` zeigt die ID-Abdeckung,
  gespeicherte RGB-/Thermalbilder und Analysepaare, bei Nullmodulen
  eine **explizite fehlende Geometrie**. Keine Kartenpunkte,
  Satellitenfotos, Modulnummern oder metrischen Positionen werden
  aus Dateinummern erfunden. Bisherige Paginierung und
  schreibgeschützte UI bleiben erhalten.
- Synthetische Regressionstests decken Projektscope, eine
  105-Beobachtungen-Paginierung, uneindeutige/fehlende Vorschläge,
  verwaiste Links, die ehrliche Nullmodulansicht und den
  unveränderten SQLite-Read-only-Zustand ab.

**Abnahmegrenze:** Dieser Schritt realisiert weder echte
Vollflug-Orthofoto-Rekonstruktion noch externe GIS-Vermessung,
RGB/Thermal-Registrierung, aus Fotos abgeleitete eindeutige
Anlagennummerierung oder die fachliche Freigabe erkannter Schäden.
Die echte Windows-10-Abnahme mit den originalen 160 Thermal-
und 33 RGB-Aufnahmen bleibt weiterhin offen, ebenso die
physische Modulzuordnung anhand unabhängig geprüfter
Referenzen. Vollständig freigegebene Phase B erst nach
Geometrie- und Kundenfachabnahme behaupten.


## Windows-10-Praxistest und Bedienoberfläche (22.10.2026)

Der echte Offline-Pilot mit 160 originalen DJI-M3T-Thermalaufnahmen und 33 RGB-Bildern bestand den gemeinsamen Import (33 technische Bildpaare), die vollständige lokale SHA-256-Originalkopien-Nachprüfung und den GUI-Neustart. 127 Thermalbilder haben kein RGB-Gegenstück; das ist für diesen Datensatz erwartet.

In der neuen Version sind die Navigationseinträge ohne Hover lesbar. Bei neuen und bearbeiteten Projektstammdaten wird die IANA-Zeitzone über eine Auswahl angeboten. Die Importseite stellt unverpackte DJI-JPG-Originale an erste Stelle; seltene ZIP-/Ordner-/GIS-Werkzeuge sind über „Weitere Importwege und Werkzeuge anzeigen“ erreichbar. Eine Sonderoption für ungepaarte Thermaldateien betrifft nur ZIP-Importe.

Für zuvor **getrennt** importierte RGB- und Thermalbilder mit noch fehlenden technischen Paaren: Über „Vorhandene RGB-/Thermalbilder technisch zuordnen“ wird die vorhandene Aufnahme-Metadatenzuordnung ausdrücklich ausgelöst. Bestehende Paare bleiben unangetastet; dieselbe Vertrauensschwelle (mindestens 0,70) wird verwendet. Diese Nachzuordnung ist **keine** geometrische RGB-/Thermalregistrierung, keine Temperaturkalibrierung und keine Expertenfreigabe. Bereits befüllte Projekte nicht erneut über den Gesamt-Originaldateiimport überschreiben.


## Technische Bildpaar-Prüfung im Offline-Projekt (22.10.2026)

Nach Import und optional bewusst ausgelöster Nachzuordnung können auf den Seiten **Import** und **Verarbeitung** die im aktiven Projekt gespeicherten RGB-/Thermal-Bildpaare geprüft werden. Die App liest dazu ausschließlich die lokalen SQLite-Metadaten: übereinstimmende DJI-Bildnummern, XMP-Zeitnähe, GPS-Nähe und die daraus bisher gespeicherte Zuordnungsbewertung. Anzeigen bleiben aggregiert; Originaldateinamen, Aufnahmezeiten und GPS-Koordinaten werden nicht ausgegeben.

**„Mit aktueller Zuordnungsregel nachvollziehbar“** bedeutet, dass das gespeicherte Paar die aktuelle konservative Regel weiterhin erfüllt und die gespeicherte Bewertung dazu passt. **„Erneut zu prüfen“** verweist auf fehlende, veraltete oder widersprüchliche Zuordnungsevidenz und löst **keine** Reparatur aus. **„RGB ohne Paar“** und **„Thermal ohne Paar“** zählen die weiteren importierten Aufnahmen ohne persistierte Zuordnung; im ersten Windows-Pilot waren 127 Thermalaufnahmen erwartungsgemäß ohne RGB-Partner. Die Angaben sind keine geometrische Registrierung, keine radiometrisch kalibrierte Temperaturmessung und keine fachliche Berichtfreigabe.

Diese Auskunft verwendet keine externen Dienste und verändert keine Projektdaten. Die nächste reale Windows-10-Bedienabnahme muss die Verständlichkeit für Laien prüfen. Farbige Akzente, optische Auflockerung und gegebenenfalls sparsame Hintergrundbilder werden in einer späteren Gestaltungsrunde abgestimmt; Lesbarkeit und Zugänglichkeit haben Vorrang.


## Optionale Expertenprüfung: RGB-/Thermal-Kontrollpunkte

Das neue Werkzeug unter **Verarbeitung → Erweitert: Kontrollpunktprüfung anzeigen** ist ein manuell auszulösender *rein lokaler, schreibgeschützter* Prüfpfad. Der normale Nutzer braucht es beim Standardimport **nicht**. Eine fachkundige Person kann eine kleine JSON-Datei mit `schema: 1`, der ID eines **bereits im aktiven Projekt gespeicherten Bildpaars** (`pair_id`), mindestens sechs unabhängigen `fit_points` und mindestens vier unabhängigen `holdout_points` auswählen. Jeder Punkt hat das Format `[thermal_x, thermal_y, rgb_x, rgb_y]`, gemessen in **nativen Pixelkoordinaten** der beiden Sensoren. Beispiel und Grenzen stehen in `docs/OFFLINE_PAIR_REGISTRATION_EXPERT_CHECK.md`.

Die Anwendung prüft Bildbezüge, Quellabmessungen, gültige Koordinaten, doppelte/überlappende Punkte, RANSAC-Inlier und unabhängige Holdout-Abweichungen. Nur zusammengefasste Qualitätszahlen oder generische Ablehnungsgründe werden angezeigt; private Bildnamen, GPS oder Bildinhalte nicht. **Die eigentliche Bildüberlagerung wird nicht ausgeführt.** Ein bestandenes Holdout liefert eine technische, **nicht freigegebene Hypothese**, keinen gültigen Bericht, keine radiometrische Temperatur, keine bestätigte physische Modulidentität und keinen Nachweis der Normkonformität. Ergebnisse werden nicht als registrierter Transformationsdatensatz gespeichert.

Für PV-Rastertests erlauben vorhandene Algorithmen weiterhin mathematisch extrapolierte Gitterkreuzungen. **Manuell eingegebene Kontrollpunkte** müssen dagegen innerhalb der aufgezeichneten Sensorbildabmessungen liegen. Die Kontrollpunkt-Auswahl und die Verständlichkeit dieser Expertenfunktion werden bei einer späteren realen Windows-10-Abnahme überprüft.


## Online-/Offline-Projektanlage (23.10.2026)

Die Eingabe ist jetzt einfacher: Bei neuen Projekten wird **„Anlage“** (3 bis 80 Zeichen) eingegeben; daraus wird der Projektname. **Projekt-ID/Nummer werden beim Speichern automatisch vergeben.** Beispielsweise `SC-0001` für das erste Projekt eines Nutzers, `SC-0002` für das nächste. Diese Nummer ist nur innerhalb des jeweiligen Nutzerkontos beziehungsweise lokalen Offline-Datenbestands eindeutig. Intern verwendet SolarCheck neue unveränderliche UUID-Projekt-IDs für Datenbankrelationen. Eine Änderung der registrierten E-Mail-Adresse beeinflusst das Projekt nicht.

Online benötigt das Formular zusätzlich die **Anlagenleistung in kWp**. Die Kontoidentität wird ausschließlich aus der gültigen Online-Sitzung genommen. Bestehende Projekte und private DJI-Bilddateien müssen weder umbenannt noch erneut importiert werden. Auch ältere, bewusst manuell angelegte IDs bleiben durch Rückwärtskompatibilität erhalten.

Für bessere Lesbarkeit sind Qt-Standardschriften 16px und Web-Standardschriften 17px; die Eingabe- und Auswahlfelder sind größer. Die endgültige Zugänglichkeit und angenehme Abstände werden im nächsten echten Windows-10-Test gemeinsam geprüft; optionale Hintergrundbilder und rein optische Elemente folgen in späteren Designschritten.
