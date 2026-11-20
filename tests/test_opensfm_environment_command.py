"""Exercise the exact client PowerShell block with inert download/Conda calls.

Native dependency installation/imports are tested separately by the real
opensfm-windows-environment workflow. No package or installer is run here.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows PowerShell 5.1")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scenario, calls", [
    ("success", 2), ("download", 0), ("checksum", 0),
    ("exists", 0), ("install", 1), ("probe", 2),
])
def test_client_command_guards_existing_prefix_and_restores_process_environment(tmp_path, scenario, calls):
    doc = (ROOT / "docs" / "OPENSFM_UMGEBUNG_WINDOWS10.md").read_text(encoding="utf-8")
    section = doc.split("<!-- tested-opensfm-environment-start -->", 1)[1]
    command = re.search(r"```powershell\n(.*?)\n```", section, re.DOTALL).group(1)
    conda = r"'E:\Tools\Miniforge3\Scripts\conda.exe'"
    assert command.count(conda) == 1
    # Bind just the external command locator to our inert function. All paths,
    # arguments, actual environment operations and exception flow stay intact.
    command = command.replace(conda, "'Test-Conda'")
    preamble = r"""
$script:Calls = 0
$script:Downloads = 0
$before = @{}
foreach ($key in @('CONDA_PKGS_DIRS','TEMP','TMP','MPLCONFIGDIR','PROJ_NETWORK')) {
    $before[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
function Join-Path {
    [CmdletBinding()]
    param([string]$Path, [string]$ChildPath)
    # The user's existing E: is not mounted on a hosted runner. Keep the real
    # Windows path-combination semantics without creating/mapping that drive.
    return [IO.Path]::Combine($Path, $ChildPath)
}
function Test-Path {
    [CmdletBinding()]
    param([string]$LiteralPath, [string]$PathType)
    if ($LiteralPath -eq 'Test-Conda') { return $true }
    if ($LiteralPath -eq 'E:\SolarCheck-OpenSfM\env') { return ($script:Scenario -eq 'exists') }
    throw 'Unexpected filesystem query'
}
function New-Item {
    [CmdletBinding()]
    param([string]$ItemType, [string[]]$Path, [switch]$Force)
    if ($ItemType -ne 'Directory') { throw 'Unexpected output type' }
    foreach ($p in $Path) {
        if ($p -notmatch '^E:\\SolarCheck-OpenSfM(?:\\|$)') { throw 'Unexpected output directory' }
    }
}
function Invoke-WebRequest {
    [CmdletBinding()]
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    $script:Downloads++
    if ($script:Scenario -eq 'download') { throw 'synthetic-download-failure' }
    $base = 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/f28bfae35c13007e4aa4dd8f4320b42ddf029e3b'
    if ($Uri -notin @("$base/config/opensfm/conda-win64-explicit.lock", "$base/scripts/MCM_SolarCheck_OPENSFM_UMGEBUNG_PRUEFUNG.py")) { throw 'Unqualified source' }
    if ($OutFile -notmatch '^E:\\SolarCheck-OpenSfM\\') { throw 'Wrong download destination' }
}
function Get-FileHash {
    [CmdletBinding()]
    param([string]$LiteralPath, [string]$Algorithm)
    if ($Algorithm -ne 'SHA256') { throw 'Wrong digest algorithm' }
    $hash = if ($LiteralPath.EndsWith('.lock')) {
        'beaa873a45ec24f1d801b81ab11b3190cdbd6aa4b53dcf77e5ebadaf4468c890'
    } else { 'e48316f5e1a5cdc28471928dd71279cf64620859f5fe76a549db24ad2821d2cf' }
    if ($script:Scenario -eq 'checksum') { $hash = '0' * 64 }
    return [pscustomobject]@{ Hash = $hash }
}
function Test-Conda {
    $script:Calls++
    $p = [Array]::IndexOf($args, '--prefix')
    if ($p -lt 0 -or $args[$p+1] -ne 'E:\SolarCheck-OpenSfM\env') { throw 'Wrong target prefix' }
    if ($env:CONDA_PKGS_DIRS -ne 'E:\SolarCheck-OpenSfM\pkgs' -or $env:TEMP -ne 'E:\SolarCheck-OpenSfM\tmp' -or $env:TMP -ne $env:TEMP -or $env:MPLCONFIGDIR -ne 'E:\SolarCheck-OpenSfM\matplotlib' -or $env:PROJ_NETWORK -ne 'OFF') { throw 'Unisolated process settings' }
    $global:LASTEXITCODE = 0
    if ($args[0] -eq 'create') {
        $f = [Array]::IndexOf($args, '--file')
        if ($f -lt 0 -or $args[$f+1] -ne 'E:\SolarCheck-OpenSfM\conda-win64-explicit.lock' -or $args -notcontains '--yes') { throw 'Wrong explicit installation' }
        if ($script:Scenario -eq 'install') { $global:LASTEXITCODE = 17 }
    } elseif ($args[0] -eq 'run') {
        if ($args -notcontains '-I' -or $args -notcontains 'python' -or $args[-1] -ne 'E:\SolarCheck-OpenSfM\MCM_SolarCheck_OPENSFM_UMGEBUNG_PRUEFUNG.py') { throw 'Wrong isolated check' }
        if ($script:Scenario -eq 'probe') { $global:LASTEXITCODE = 18 }
    } else { throw 'Unexpected Conda action' }
}
"""
    tail = r"""
$caught = $false
try {
__COMMAND__
} catch {
    $caught = $true
    $expected = switch ($script:Scenario) {
        'download' { 'synthetic-download-failure' }
        'checksum' { 'Lock-Pruefsumme stimmt nicht.' }
        'exists' { 'Zielumgebung existiert bereits; bitte melden, nicht loeschen.' }
        'install' { 'Umgebungseinrichtung fehlgeschlagen.' }
        'probe' { 'Umgebungspruefung fehlgeschlagen.' }
        default { 'no-error-expected' }
    }
    if ($_.Exception.Message -ne $expected) { throw }
}
if ($caught -ne ($script:Scenario -ne 'success')) { throw 'Incorrect error outcome' }
if ($script:Calls -ne $script:ExpectedCalls) { throw 'Unexpected Conda invocation count' }
if ($script:Scenario -eq 'exists' -and $script:Downloads -ne 0) { throw 'Existing prefix was touched' }
foreach ($key in $before.Keys) {
    if ([Environment]::GetEnvironmentVariable($key, 'Process') -ne $before[$key]) { throw "Process setting not restored: $key" }
}
Write-Output 'ENVIRONMENT_COMMAND_CONTRACT_PASSED'
"""
    settings = f"\n$script:Scenario = '{scenario}'\n$script:ExpectedCalls = {calls}\n"
    script = tmp_path / "environment-command.ps1"
    script.write_text(preamble + settings + tail.replace("__COMMAND__", command), encoding="utf-8-sig")
    ps = shutil.which("powershell.exe")
    assert ps, "Native PowerShell verification is required on Windows"
    result = subprocess.run(
        [ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ENVIRONMENT_COMMAND_CONTRACT_PASSED" in result.stdout
