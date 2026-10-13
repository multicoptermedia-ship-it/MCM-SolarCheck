# Verarbeitung im gemeinsamen Browserfrontend

Für die Online-Anwendung wurde `POST /api/project-process?project_id=…&job_id=…` ergänzt. Die Route verwendet **denselben** authentifizierten `ProjectProcessingService` wie der bestehende HTML-Endpunkt. Sie prüft Session und Kundenzugang, und der Dienst ist für die Prüfung der Projekt-/Job-Zuordnung zuständig. Nur dessen tatsächlich zurückgegebene Werte (`state`, Thermalbildzahl, Bildpaare, Importfehler) werden als JSON ausgegeben.

Das gemeinsame Frontend erlaubt die Verarbeitung nur mit **bereits vorhandener Job-ID**. Es legt keinen Job automatisch an, startet keine Verarbeitung ohne Job und behauptet keine Fertigstellung bei Fehlern. Die Erzeugung und Anzeige gültiger Verarbeitungsaufträge, Offline-Verarbeitung, Fortschrittsabfrage und detaillierte Befunde müssen noch separat integriert werden. Demo-, Zahlungs- und Berichtsschranken bleiben unverändert.
