"""Customer output must not expose internal implementation identifiers."""
from mcm_solarcheck.services.pv_pilot_ai_assessment import PilotAIAssessment
from mcm_solarcheck.services.pv_pilot_ai_provenance import PilotAIProvenance
from mcm_solarcheck.services.pv_pilot_customer_view import customer_ai_lines


def test_customer_output_contains_only_relevant_assessment():
    metadata = PilotAIProvenance("secret-model", "internal-version", "private-frame", 0.93, "accepted")
    assessment = PilotAIAssessment(
        "classified_suspicion", "Bypassdiodenfehler",
        "Elektrische Prüfung empfohlen.", metadata,
    )
    text = " ".join(customer_ai_lines(assessment))
    assert "Verdacht auf Bypassdiodenfehler" in text
    assert "Elektrische Prüfung empfohlen." in text
    for secret in ("secret-model", "internal-version", "private-frame", "93", "accepted"):
        assert secret not in text


def test_missing_and_unassigned_are_readable():
    assert "nicht erfasst" in customer_ai_lines(None)[0]
    assert "nicht eindeutig" in customer_ai_lines(PilotAIAssessment("unassigned"))[0]
    assert "Keine Auffälligkeit" in customer_ai_lines(PilotAIAssessment("no_anomaly"))[0]
