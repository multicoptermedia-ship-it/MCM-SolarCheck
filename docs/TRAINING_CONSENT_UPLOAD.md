# Upload-Einwilligung (Zwischenstand)

Im gemeinsamen Frontend erscheint beim Online-Upload eine standardmäßig nicht markierte, freiwillige Checkbox. Der Browser sendet `X-SolarCheck-Training-Consent: granted|declined`. Der HTTP-Server akzeptiert ausschließlich diese Werte. Bei `granted` ohne konfigurierten Audit-Service wird der Upload vor dem Schreiben abgelehnt (503). Nach erfolgreichem Upload wird `TrainingConsentService.grant` mit der authentifizierten Kunden-ID und Projekt-ID aufgerufen.

**Noch keine vollständige Produktivintegration:** Der Online-Composition-Layer konfiguriert noch keinen persistenten Audit-Service; ein echtes Opt-in schlägt daher derzeit sicher fehl. Die Reihenfolge Upload → Audit ist nicht transaktional: Ein Fehler beim Audit kann einen bereits gespeicherten Upload hinterlassen. Bis zur atomaren Integration dürfen diese Daten niemals als Trainingseinwilligung gelten. Die separate Widerrufs-HTTP-Route, Datenbankverdrahtung, rechtsgeprüfter Einwilligungstext mit verlinkter Datenschutzerklärung und die Übernahme freigegebener Trainingskopien fehlen. Keine automatische KI-Trainingsnutzung ist aktiviert.

Der bestehende Offline-Upload wird nicht eingeschränkt. Die 14-Tage-Löschfrist wird gesondert implementiert.
