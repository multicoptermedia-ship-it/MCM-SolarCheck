"""Run the pasted client build command with inert native tools on Windows."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Native PowerShell 5.1")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scenario, calls", [
    ("success", 3), ("exists", 0), ("download", 0), ("checksum", 0),
    ("fetch", 0), ("revision", 0), ("build", 1), ("opencl", 1),
    ("install", 2), ("probe", 3), ("resume", 3), ("resume_bad_hash", 3),
])
@pytest.mark.parametrize("existing_git_config", [False, True])
def test_build_command_stops_before_install_on_failure_and_restores_settings(tmp_path, scenario, calls, existing_git_config):
    doc = (ROOT / "docs/OPENSFM_QUELLBAU_WINDOWS10.md").read_text(encoding="utf-8")
    section = doc.split("<!-- tested-opensfm-source-build-start -->", 1)[1]
    command = re.search(r"```powershell\n(.*?)\n```", section, re.S).group(1)
    command = command.replace("'E:\\Tools\\Miniforge3\\Scripts\\conda.exe'", "'Test-Conda'")
    command = command.replace("Join-Path $prefix 'Library\\bin\\git.exe'", "'Test-SourceGit'")
    preamble = r"""
# Only this disposable PowerShell child is changed, never the host's config.
foreach ($key in @('GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0','GIT_CONFIG_KEY_1','GIT_CONFIG_VALUE_1','GIT_CONFIG_KEY_2','GIT_CONFIG_VALUE_2')) {
    [Environment]::SetEnvironmentVariable($key, $null, 'Process')
}
if ($script:ExistingGitConfig) {
    $env:GIT_CONFIG_COUNT = '1'
    $env:GIT_CONFIG_KEY_0 = 'user.synthetic'
    $env:GIT_CONFIG_VALUE_0 = 'preserved'
}
$before = @{}
foreach ($key in @('CONDA_PKGS_DIRS','TEMP','TMP','MPLCONFIGDIR','PROJ_NETWORK','CMAKE_GENERATOR','CMAKE_BUILD_PARALLEL_LEVEL','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0','GIT_CONFIG_KEY_1','GIT_CONFIG_VALUE_1','GIT_CONFIG_KEY_2','GIT_CONFIG_VALUE_2')) {
    $before[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
$script:Calls = 0
$script:Fetches = 0
$script:Downloads = 0
$script:Inits = 0
$script:Checkouts = 0
function Assert-GitScope {
    $start = if ($script:ExistingGitConfig) { 1 } else { 0 }
    if ([int]$env:GIT_CONFIG_COUNT -ne $start + 2) { throw 'Wrong Git config count' }
    if ($script:ExistingGitConfig -and ($env:GIT_CONFIG_KEY_0 -ne 'user.synthetic' -or $env:GIT_CONFIG_VALUE_0 -ne 'preserved')) { throw 'Existing Git settings overwritten' }
    $safePaths = @()
    foreach ($i in @($start, ($start+1))) {
        if ([Environment]::GetEnvironmentVariable("GIT_CONFIG_KEY_$i", 'Process') -ne 'safe.directory') { throw 'Wrong Git exception key' }
        $safePaths += [Environment]::GetEnvironmentVariable("GIT_CONFIG_VALUE_$i", 'Process')
    }
    if ($safePaths[0] -notmatch '^E:/SolarCheck-OpenSfM/build-[0-9a-f]{32}/source$' -or $safePaths[1] -ne ($safePaths[0] -replace '/source$', '/opencl-clhpp')) { throw 'Git exception outside the two repositories' }
}
function Join-Path {
    param([string]$Path, [string]$ChildPath)
    [IO.Path]::Combine($Path, $ChildPath)
}
function Test-Path {
    param([string]$LiteralPath, [string]$PathType)
    if ($LiteralPath -in @('Test-Conda','Test-SourceGit','E:\SolarCheck-OpenSfM\env\python.exe')) { return $true }
    if ($LiteralPath -eq 'E:\SolarCheck-OpenSfM\env\Lib\site-packages\opensfm') { return ($script:Scenario -eq 'exists') }
    if ($LiteralPath -match '\\build-[0-9a-f]{32}\\buildcheck.py$') { return $true }
    if ($LiteralPath -match '\\build-[0-9a-f]{32}\\source\\.git$') { return ($script:Scenario -in @('resume','resume_bad_hash') -and $LiteralPath.Contains(('a' * 32))) }
    if ($LiteralPath -match '\\build-[0-9a-f]{32}\\opencl-clhpp\\.git$') { return $false }
    throw 'Unexpected file query'
}
function New-Item {
    [CmdletBinding()]
    param([string]$ItemType, [string[]]$Path, [switch]$Force)
    foreach ($p in $Path) {
        if ($p -notmatch '^E:\\SolarCheck-OpenSfM\\(build-[0-9a-f]{32}|tmp|matplotlib)$') { throw 'Unexpected write destination' }
        if ($script:Scenario -eq 'resume' -and $p.EndsWith(('a' * 32))) { throw 'Existing build directory was recreated' }
    }
}
function Invoke-WebRequest {
    [CmdletBinding()]
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
    $script:Downloads++
    if ($Uri -ne 'https://raw.githubusercontent.com/multicoptermedia-ship-it/MCM-SolarCheck/1085a6ad774bd1a67c371c868b34853c8f95d462/scripts/MCM_SolarCheck_OPENSFM_BUILD_PRUEFUNG.py') { throw 'Unpinned probe' }
    if ($script:Scenario -eq 'download') { throw 'synthetic-download-error' }
}
function Get-FileHash {
    param([string]$LiteralPath, [string]$Algorithm)
    $hash = '426877f7135cc94669af14cd617a740e4f45808547f7037e1380e00e15990349'
    if ($script:Scenario -eq 'checksum') { $hash = '0' * 64 }
    if ($script:Scenario -eq 'resume_bad_hash' -and $LiteralPath.Contains(('a' * 32))) { $hash = '0' * 64 }
    [pscustomobject]@{ Hash = $hash }
}
function Test-SourceGit {
    Assert-GitScope
    $global:LASTEXITCODE = 0
    if ($args[0] -eq 'init') { $script:Inits++; return }
    if ($args[2] -eq 'fetch') {
        $script:Fetches++
        if ($args[3] -ne '--depth' -or $args[4] -ne '1') { throw 'Unbounded source fetch' }
        $expected = if ($script:Fetches -eq 1) {
            @('https://github.com/OpenSfM/OpenSfM.git','refs/tags/v1.1')
        } else { @('https://github.com/KhronosGroup/OpenCL-CLHPP.git','refs/tags/v2025.07.22') }
        if ($args[5] -ne $expected[0] -or $args[6] -ne $expected[1]) { throw 'Wrong source pin' }
        if ($script:Scenario -eq 'fetch') { $global:LASTEXITCODE = 7 }
        return
    }
    if ($args[2] -eq 'checkout') { $script:Checkouts++; return }
    if ($args[2] -eq 'rev-parse') {
        if ($script:Scenario -eq 'revision') { return ('0' * 40) }
        if ($script:Fetches -eq 1) { return '8b6b77efddebf4429044d3206c7dc21c4e767e08' }
        return '2a608428f725cad7903ef55e1ce5b995895838f5'
    }
    throw 'Unexpected Git invocation'
}
function Get-Content {
    param([string]$Path, [switch]$Raw)
    if ($script:Scenario -eq 'opencl') { return 'OPENSFM_HAVE_OPENCL:BOOL=OFF' }
    return 'OPENSFM_HAVE_OPENCL:BOOL=ON'
}
function Get-ChildItem {
    param([string]$Path, [string]$LiteralPath, [string]$Filter, [switch]$File, [switch]$Directory)
    if ($Directory) {
        if ($LiteralPath -ne 'E:\SolarCheck-OpenSfM') { throw 'Unexpected directory search' }
        if ($script:Scenario -in @('resume','resume_bad_hash')) {
            return [pscustomobject]@{ Name=('build-' + ('a' * 32)); FullName=('E:\SolarCheck-OpenSfM\build-' + ('a' * 32)); CreationTime=[datetime]'2026-11-08' }
        }
        return
    }
    if ($script:Scenario -eq 'resume' -and -not $Path.Contains(('a' * 32))) { throw 'Build was not resumed' }
    if ($script:Scenario -eq 'resume_bad_hash' -and $Path.Contains(('a' * 32))) { throw 'Unqualified existing build was used' }
    [pscustomobject]@{ FullName = "$Path\opensfm-test.whl" }
}
function Test-Conda {
    Assert-GitScope
    $script:Calls++
    $global:LASTEXITCODE = 0
    $index = [Array]::IndexOf($args, '--prefix')
    if ($index -lt 0 -or $args[$index+1] -ne 'E:\SolarCheck-OpenSfM\env') { throw 'Wrong Python prefix' }
    if ($env:TEMP -ne 'E:\SolarCheck-OpenSfM\tmp' -or $env:PROJ_NETWORK -ne 'OFF' -or $env:CMAKE_GENERATOR -ne 'Visual Studio 17 2022' -or $env:CMAKE_BUILD_PARALLEL_LEVEL -ne '2') { throw 'Wrong child settings' }
    if ($args -contains 'wheel') {
        foreach ($flag in @('--no-deps','--no-index','--no-build-isolation','--config-settings=build.tool-args=/m:2')) {
            if ($args -notcontains $flag) { throw 'Unqualified build options' }
        }
        if ($script:Scenario -eq 'build') { $global:LASTEXITCODE = 7 }
    } elseif ($args -contains 'install') {
        if ($script:Scenario -eq 'install') { $global:LASTEXITCODE = 7 }
    } elseif ($args -contains '-I') {
        if ($script:Scenario -eq 'probe') { $global:LASTEXITCODE = 7 }
    } else { throw 'Unexpected Conda invocation' }
}
"""
    tail = r"""
$caught = $false
try {
__COMMAND__
} catch {
    $caught = $true
    $expected = switch ($script:Scenario) {
        'exists' { 'OpenSfM ist bereits vorhanden; bitte melden, nicht ueberschreiben.' }
        'download' { 'synthetic-download-error' }
        'checksum' { 'Buildpruefung-Pruefsumme stimmt nicht.' }
        'fetch' { 'Quelltextdownload OpenSfM fehlgeschlagen, Git-Exitcode: 7. Bitte die Git-Fehlerzeile davor beachten.' }
        'revision' { 'Quellcommit stimmt nicht.' }
        'build' { 'OpenSfM-Quellbau fehlgeschlagen; lokales pip-build.log erhalten.' }
        'opencl' { 'OpenCL-Unterstuetzung wurde nicht mitgebaut.' }
        'install' { 'Installation des selbst gebauten Pakets fehlgeschlagen.' }
        'probe' { 'OpenSfM-Buildpruefung fehlgeschlagen.' }
        default { 'No-error-expected' }
    }
    if ($_.Exception.Message -ne $expected) { throw }
}
if ($caught -ne ($script:Scenario -notin @('success','resume','resume_bad_hash'))) { throw 'Incorrect error outcome' }
if ($script:Calls -ne $script:ExpectedCalls) { throw 'Unexpected build/install/probe count' }
if ($script:Scenario -eq 'exists' -and $script:Downloads -ne 0) { throw 'Existing engine was touched' }
if ($script:Scenario -eq 'resume' -and $script:Inits -ne 1) { throw 'Existing source repository was reinitialized' }
if ($script:Scenario -in @('fetch','revision') -and $script:Checkouts -ne 0) { throw 'Unverified source was checked out' }
foreach ($key in $before.Keys) {
    if ([Environment]::GetEnvironmentVariable($key, 'Process') -ne $before[$key]) { throw "Setting not restored: $key" }
}
Write-Output 'SOURCE_BUILD_COMMAND_CONTRACT_PASSED'
"""
    settings = f"\n$script:Scenario = '{scenario}'\n$script:ExpectedCalls = {calls}\n$script:ExistingGitConfig = ${str(existing_git_config).lower()}\n"
    script = tmp_path / "source-build-command.ps1"
    script.write_text(settings + preamble + tail.replace("__COMMAND__", command), encoding="utf-8-sig")
    ps = shutil.which("powershell.exe")
    assert ps
    result = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'SOURCE_BUILD_COMMAND_CONTRACT_PASSED' in result.stdout
