# Freiwillige KI-Trainingseinwilligung – Umsetzung in Etappen

Dieser Block liefert den append-only SQLite-Auditstore und den kundengeprüften Service für `grant` und `withdraw`. Er speichert Kunden-ID, Projekt-ID, Ereignis, UTC-Zeitpunkt und die Version des Einwilligungstextes. Die aktuelle Berechtigung wird ausschließlich aus dem letzten Ereignis abgeleitet. Der Service benötigt dieselbe `project_belongs_to_customer(customer_id, project_id)`-Prüfung wie der bestehende Uploadservice.

**Noch offen und deshalb nicht produktiv nutzbar:** Checkbox im gemeinsamen Uploadformular (standardmäßig leer), authentifizierte HTTP-Endpunkte, serverseitige Verknüpfung mit dem Uploadvorgang, dauerhafte Verdrahtung in `OnlinePersistence`, Datenschutzinformationen, Widerrufsoberfläche und Löschung bereits erzeugter Trainingskopien. Keine Bilder werden derzeit für Training kopiert oder zum Training freigegeben. Eine Browser-Checkbox allein ist kein belastbarer Nachweis; die serverseitige Zuordnung und die exakt angezeigte Textversion müssen beim tatsächlichen Upload geprüft werden.

Die Löschfrist für Kundenprojekte (14 Tage nach definiertem Exportereignis) und die getrennte Behandlung rechtmäßig freigegebener Trainingskopien werden in späteren Blöcken umgesetzt. Kein Merge nach `main`.
