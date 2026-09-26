"""Framework-neutral shell policy derived from deployment capabilities."""

from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.deployment import DeploymentMode, entry_capabilities


@dataclass(frozen=True)
class ShellPolicy:
    deployment: DeploymentMode
    initial_route: str
    show_login: bool
    show_trial_entry: bool
    show_commercial_entry: bool
    show_user_guide_hint: bool = True


def shell_policy(deployment: DeploymentMode) -> ShellPolicy:
    """Return presentation policy without duplicating deployment rules in the GUI."""
    capabilities = entry_capabilities(deployment)

    if capabilities.login_required:
        initial_route = "login"
    else:
        initial_route = "project"

    return ShellPolicy(
        deployment=deployment,
        initial_route=initial_route,
        show_login=capabilities.login_required,
        show_trial_entry=capabilities.trial_selection_available,
        show_commercial_entry=(
            capabilities.commercial_quote_required
            or capabilities.online_payment_required
        ),
    )
