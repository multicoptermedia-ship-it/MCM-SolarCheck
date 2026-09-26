"""Shared GUI command contract for SolarCheck shells.

This module intentionally contains no Qt widgets.  The PySide6 shell binds these
commands to menus/buttons so both surfaces invoke the same application action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_policy import shell_policy


class ShellCommandId(str, Enum):
    NEW_PROJECT = "new_project"
    OPEN_PROJECT = "open_project"
    IMPORT = "import"
    PROCESS = "process"
    PLANT_OVERVIEW = "plant_overview"
    REVIEW = "review"
    REPORT = "report"
    EXPORT = "export"
    USER_GUIDE = "user_guide"


@dataclass(frozen=True)
class ShellCommand:
    command_id: ShellCommandId
    label: str


_COMMON_COMMANDS = (
    ShellCommand(ShellCommandId.NEW_PROJECT, "New project"),
    ShellCommand(ShellCommandId.OPEN_PROJECT, "Open project"),
    ShellCommand(ShellCommandId.IMPORT, "Import"),
    ShellCommand(ShellCommandId.PROCESS, "Processing"),
    ShellCommand(ShellCommandId.PLANT_OVERVIEW, "Plant overview"),
    ShellCommand(ShellCommandId.REVIEW, "Review"),
    ShellCommand(ShellCommandId.REPORT, "Report"),
    ShellCommand(ShellCommandId.EXPORT, "Export"),
    ShellCommand(ShellCommandId.USER_GUIDE, "User guide"),
)


def shell_commands(deployment: DeploymentMode) -> tuple[ShellCommand, ...]:
    """Return shared workflow commands after validating the deployment shell."""
    shell_policy(deployment)
    return _COMMON_COMMANDS
