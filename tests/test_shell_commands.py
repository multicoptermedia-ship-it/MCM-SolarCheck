from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_commands import ShellCommandId, shell_commands


def test_online_and_offline_share_same_workflow_command_ids() -> None:
    online = shell_commands(DeploymentMode.ONLINE)
    offline = shell_commands(DeploymentMode.OFFLINE_DESKTOP)

    assert tuple(command.command_id for command in online) == tuple(
        command.command_id for command in offline
    )


def test_shared_commands_cover_frozen_workflow_and_help() -> None:
    ids = {command.command_id for command in shell_commands(DeploymentMode.ONLINE)}

    assert ids == {
        ShellCommandId.NEW_PROJECT,
        ShellCommandId.OPEN_PROJECT,
        ShellCommandId.IMPORT,
        ShellCommandId.PROCESS,
        ShellCommandId.PLANT_OVERVIEW,
        ShellCommandId.REVIEW,
        ShellCommandId.REPORT,
        ShellCommandId.EXPORT,
        ShellCommandId.USER_GUIDE,
    }


def test_command_ids_are_unique() -> None:
    commands = shell_commands(DeploymentMode.OFFLINE_DESKTOP)
    ids = [command.command_id for command in commands]

    assert len(ids) == len(set(ids))
