# Vertikaler Berichtsanschluss – überprüfte Schnittstellen

Stand 2026-10-11, Entwicklungsbranch.

- `reporting/report_model.py`: `InspectionReport` verlangt echte Projektdaten, zeitbewussten Prüfbeginn, Prüfer und plausible Modulzahlen. `ModuleReportDetail` erlaubt ausschließlich fachlich geprüfte Zustände `confirmed` oder `unclear`.
- `reporting/export.py:export_report` exportiert `InspectionReport` über bestehende Renderer nach DOCX, ODT oder PDF. Der Renderer ist **kein eigener Freigabe- oder Zahlungsnachweis**.
- `services/vertical_expert_review.py`: ein `ExpertReviewRecord` hält angenommene/verworfene Kandidaten und Freigabe fest, der bisherige `ReviewedDecision` transportiert aber **nicht** die Einzelentscheidungen.
- `services/vertical_reviewed_m3t_composition.py`: bisher wird lediglich ein Evidenzmanifest erstellt, noch kein Kundenbericht.

## Qualitätsgrenzen
Ein Importkandidat ist kein bestätigter PV-Schaden. Die Berichtsanbindung darf nur ausdrücklich angenommene Kandidaten mit fachlich dokumentierter Zuordnung zu einem Modul übernehmen. Fehlende Modulanzahl, Standort-/Kunden-/Prüfdaten oder Freigabe werden nicht geschätzt. Celsiuswerte ohne validierte radiometrische Provenienz bleiben aus dem Bericht. Export wird nur über einen gesonderten Freigabe-Guard aufgerufen. Online-Zahlung und Auslieferung sind weiterhin separate Gates.

## Nächster Schritt
Einen streng validierten Review-zu-Report-Adapter mit unveränderlichem Review-Snapshot und einen kontrollierten DOCX/ODT/PDF-Export testen. Noch kein produktiver Online-Workflow.
