"""Presentation-neutral navigation model for the SolarCheck application shell."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_policy import shell_policy


class ShellRoute(str, Enum):
    LOGIN = "login"
    PROJECT = "project"
    IMPORT = "import"
    PROCESSING = "processing"
    PLANT_OVERVIEW = "plant_overview"
    REVIEW = "review"
    REPORT = "report"
    EXPORT = "export"


@dataclass(frozen=True)
class ShellNavigation:
    deployment: DeploymentMode
    initial_route: ShellRoute
    workflow_routes: tuple[ShellRoute, ...]


_WORKFLOW_ROUTES = (
    ShellRoute.PROJECT,
    ShellRoute.IMPORT,
    ShellRoute.PROCESSING,
    ShellRoute.PLANT_OVERVIEW,
    ShellRoute.REVIEW,
    ShellRoute.REPORT,
    ShellRoute.EXPORT,
)


def shell_navigation(deployment: DeploymentMode) -> ShellNavigation:
    policy = shell_policy(deployment)
    initial_route = (
        ShellRoute.LOGIN if policy.initial_route == "login" else ShellRoute.PROJECT
    )
    return ShellNavigation(
        deployment=deployment,
        initial_route=initial_route,
        workflow_routes=_WORKFLOW_ROUTES,
    )
