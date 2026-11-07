"""Run the actual user command under Windows PowerShell with inert setup stubs.

No Microsoft installer, download, E: directory or user project is touched.
This guards the documented interactive-parameter contract behind exit code 87.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PowerShell")
ROOT = Path(__file__).resolve().parents[1]


def user_command():
    text = (ROOT / "docs" / "OPENSFM_MINIFORGE_WINDOWS10.md").read_text(encoding="utf-8")
    section = text.split("<!-- tested-buildtools-interactive-start -->", 1)[1]
    return re.search(r"```powershell\n(.*?)\n```", section, re.DOTALL).group(1)


def run_command(tmp_path, exit_code=0, download_error=False):
    powershell = shutil.which("powershell.exe")
    assert powershell, "The native PowerShell verification is required on Windows"
    # Cmdlet-compatible stubs exercise the real PowerShell argument binding.
    preamble = r"""
$ErrorActionPreference = 'Stop'
$script:Started = $false
function New-Item {
    [CmdletBinding()]
    param([string]$ItemType, [string]$Path, [switch]$Force)
    if ($ItemType -ne 'Directory' -or $Path -match '^C:') { throw 'invalid setup destination' }
}
function Invoke-WebRequest {
    [CmdletBinding()]
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    if ($Uri -ne 'https://aka.ms/vs/17/release/vs_BuildTools.exe') { throw 'wrong bootstrapper family/source' }
    if ($script:DownloadError) { throw 'synthetic-download-failure' }
}
function Get-ChildItem { throw 'ambiguous Downloads selection is forbidden' }
function Start-Process {
    [CmdletBinding()]
    param([string]$FilePath, [string[]]$ArgumentList, [switch]$Wait, [switch]$PassThru)
    $script:Started = $true
    if (!$Wait -or !$PassThru -or $ArgumentList -notcontains '--wait') { throw 'missing lifecycle observation' }
    $hasQuiet = $ArgumentList -contains '--quiet'
    $hasPassive = $ArgumentList -contains '--passive'
    if ($ArgumentList -contains '--norestart' -and !$hasQuiet -and !$hasPassive) {
        return [pscustomobject]@{ ExitCode = 87 }
    }
    if ($hasQuiet -or $hasPassive) { throw 'disk-space review must remain interactive' }
    $paths = @()
    for ($i = 0; $i -lt $ArgumentList.Count; $i++) {
        if ($ArgumentList[$i] -eq '--installPath') { $paths += $ArgumentList[$i + 1] }
        if ($ArgumentList[$i] -eq '--path') { $paths += ($ArgumentList[$i + 1] -split '=', 2)[1] }
    }
    if ($paths.Count -ne 3 -or ($paths | Where-Object { $_ -notmatch '^[D-Z]:\\' })) {
        throw 'product/cache/shared must remain off C'
    }
    return [pscustomobject]@{ ExitCode = $script:InstallerExit }
}
"""
    settings = f"\n$script:InstallerExit = {exit_code}\n$script:DownloadError = ${str(download_error).lower()}\n"
    if download_error:
        run = """
try {
__COMMAND__
    throw 'expected download failure was not observed'
} catch {
    if ($script:Started -or $_.Exception.Message -ne 'synthetic-download-failure') { throw }
    Write-Output 'DOWNLOAD_BLOCKED_BEFORE_INSTALLER_START'
}
"""
    else:
        run = "\n__COMMAND__\nif (!$script:Started) { throw 'installer command was not reached' }\n"
    script = tmp_path / "interactive-command-contract.ps1"
    script.write_text(preamble + settings + run.replace("__COMMAND__", user_command()), encoding="utf-8-sig")
    # Bypass is confined to this CI child process executing our inert fixture.
    # The user command itself needs no execution-policy or security changes.
    return subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize("exit_code", [0, 87])
def test_interactive_command_is_valid_and_exposes_actual_exit(tmp_path, exit_code):
    result = run_command(tmp_path, exit_code=exit_code)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Installer-Exitcode: {exit_code}" in result.stdout


def test_failed_download_cannot_start_stale_bootstrapper(tmp_path):
    result = run_command(tmp_path, download_error=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DOWNLOAD_BLOCKED_BEFORE_INSTALLER_START" in result.stdout
