from mcm_solarcheck.domain.operator_profile import OperatorProfile


def test_operator_profile_keeps_report_branding_configurable():
    profile=OperatorProfile("Example Inspection GmbH","Solarstr. 1","12345","Musterstadt","office@example.invalid",logo_path="logo.png")
    assert profile.company_name=="Example Inspection GmbH"
    assert profile.address=="Solarstr. 1, 12345 Musterstadt"
    assert profile.logo_path=="logo.png"
