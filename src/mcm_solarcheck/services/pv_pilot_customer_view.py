"""Customer-facing projection without internal AI model metadata."""


def customer_ai_lines(assessment):
    if assessment is None:
        return ("KI-Auswertung: nicht erfasst", "Fachliche Bewertung: nicht dokumentiert")
    if assessment.status == "classified_suspicion":
        label = "Mögliche Ursache: Verdacht auf " + assessment.suggested_cause
    elif assessment.status == "unassigned":
        label = "Auffälligkeit erkannt - Ursache nicht eindeutig zuzuordnen"
    else:
        label = "Keine Auffälligkeit erkannt"
    return (label, "Fachliche Bewertung: " + (assessment.expert_assessment or "nicht dokumentiert"))
