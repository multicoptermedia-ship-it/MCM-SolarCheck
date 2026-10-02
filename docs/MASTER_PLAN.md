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
- Phase 10L: End-to-End Online Payment Integration – laufender Block.
- Phase 10M: Operational Readiness / Deployment Gates – folgt erst nach vollständig grünem 10L.
- Phase 11: öffentlicher Produktbetrieb / Expansion – nicht begonnen.

## Phase 10L – verifizierter Teilstand

Die Teilblöcke **10L.1 bis 10L.8** sind implementiert und nach CI-Gate grün.

- 10L.1: Registration- und Compute-Persistenz produktiv komponiert.
- 10L.2: Billing an autoritativ abgeschlossenen Compute Job gebunden.
- 10L.3: Delivery → Billing Release → Capture integriert.
- 10L.4: persistentes Pricing, Merchant Stores und Checkout komponiert.
- 10L.5: vollständiger Card-Lifecycle als E2E-Pfad.
- 10L.6: Registration Service produktiv komponiert und persistiert.
- 10L.7: verifiziertes Produkt-Entitlement persistent gemacht; Online-Compute-Erstellung erfordert aktives Entitlement.
- 10L.8: Checkout erfordert einen zum Job, Nutzer und Projekt passenden Billing-Kontext; ohne diesen Kontext wird kein Payment erzeugt.

Letztes verifiziertes Gate für 10L.8: GitHub Actions Run #1570, Python 3.11 und 3.12 erfolgreich.

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

## Nächste Arbeit in 10L

Die verbleibenden End-to-End-Pfade werden einzeln mit denselben Gates geschlossen. Priorität haben:

1. PayPal als vollständiger komponierter Online-Pfad einschließlich Delivery-Gate.
2. SEPA als eigener asynchroner Online-Pfad einschließlich Reconciliation.
3. Negativpfad: fehlgeschlagene Reportzustellung darf Billing Release und endgültige Zahlung nicht auslösen.
4. Gesamtcheck von Phase 10L.

Erst danach beginnt 10M.

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

## Architekturprinzip Online / Offline

Online und Offline teilen ab dem eigentlichen SolarCheck-Projektworkflow denselben fachlichen Domain-Core. Online ergänzt Identität, Entitlement, serverseitige Compute-/Delivery-/Billing-/Payment-Orchestrierung. Offline darf diese Online-spezifischen Zugangsschichten nicht benötigen, muss aber dieselben fachlichen Review-, Provenienz- und Report-Gates respektieren.

Die menschliche Fachprüfung bleibt maßgeblich. Fehlende Evidenz darf nicht künstlich erzeugt werden. Unklare Freigabezustände werden fail-closed behandelt. Technische Softwarefreigabe, wissenschaftliche Modellvalidierung, Normprüfung und kommerzielle Produktfreigabe bleiben getrennte Gates.
