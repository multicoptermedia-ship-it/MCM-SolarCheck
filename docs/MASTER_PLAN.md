# SolarCheck – Operativer Masterplan und Projektstatus

Stand: 2026-10-02

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
- Phase 10M: Operational Readiness / Deployment Gates – laufender Block.
- Phase 11: öffentlicher Produktbetrieb / Expansion – nicht begonnen.

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

## Nächster Hauptblock: Phase 11 – Public Product Operation / Expansion

Phase 11 beginnt erst nach grünem CI-Gate dieses 10M-Abschlussstands. Der konkrete erste Unterblock wird aus dem dann aktuellen Repository-Stand abgeleitet; bestehende Readiness-, Activation-, Customer-Entry- und 10L-Fachgates dürfen nicht umgangen werden.

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

Die menschliche Fachprüfung bleibt maßgeblich. Fehlende Evidenz darf nicht künstlich erzeugt werden. Unklare Freigabezustände werden fail-closed behandelt. Technische Softwarefreigabe, wissenschaftliche Modellvalidierung, Normprüfung und kommerzielle Produktfreigabe bleiben getrennte Gates.
