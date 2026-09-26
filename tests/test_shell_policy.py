from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_policy import shell_policy


def test_online_shell_starts_at_login_with_online_entry_options() -> None:
    policy = shell_policy(DeploymentMode.ONLINE)

    assert policy.initial_route == "login"
    assert policy.show_login is True
    assert policy.show_trial_entry is True
    assert policy.show_commercial_entry is True
    assert policy.show_user_guide_hint is True


def test_offline_shell_starts_at_project_without_online_entry_options() -> None:
    policy = shell_policy(DeploymentMode.OFFLINE_DESKTOP)

    assert policy.initial_route == "project"
    assert policy.show_login is False
    assert policy.show_trial_entry is False
    assert policy.show_commercial_entry is False
    assert policy.show_user_guide_hint is True
