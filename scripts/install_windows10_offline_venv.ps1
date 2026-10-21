# Offline-only Windows 10 development environment setup from pre-fetched wheels.
# Never accesses pip indexes or updates the existing environment, DB or OS.
param(
    [Parameter(Mandatory=$true)][string]$Wheelhouse
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This script requires Windows; Windows 10 is the supported target.'
}
if (-not [IO.Path]::IsPathRooted($Wheelhouse) -or -not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
    throw 'An existing, absolute wheelhouse directory is required.'
}
$root = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path $root 'requirements.txt'
$python = (Get-Command python -ErrorAction Stop).Source
& $python -c "import sys,struct; assert sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8, 'Requires 64-bit Python 3.11'"
if ($LASTEXITCODE -ne 0) { throw 'Requires 64-bit Python 3.11.' }
$venv = Join-Path $root '.venv'
if (Test-Path -LiteralPath $venv) {
    throw 'Existing .venv will not be overwritten. Inspect or remove it yourself first.'
}
$beforePythonPath = $env:PYTHONPATH
$beforeNoIndex = $env:PIP_NO_INDEX
$beforeNoInput = $env:PIP_NO_INPUT
$beforePipVersion = $env:PIP_DISABLE_PIP_VERSION_CHECK
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    & $python -m mcm_solarcheck.offline.wheelhouse verify --wheelhouse $Wheelhouse --requirements $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Wheelhouse verification failed; no virtualenv created.' }
    $env:PIP_NO_INDEX = '1'
    $env:PIP_NO_INPUT = '1'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    & $python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create local Python virtualenv.' }
    $venvPython = Join-Path $venv 'Scripts\python.exe'
    & $venvPython -m pip --disable-pip-version-check install --no-index --only-binary=:all: --find-links $Wheelhouse --requirement $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Offline install failed; .venv may be incomplete; do not run the app.' }
    & $venvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Installed dependency conflicts found; do not run the app.' }
    & $venvPython -m mcm_solarcheck.offline.windows_smoke --headless
    if ($LASTEXITCODE -ne 0) { throw 'Offline desktop smoke failed; do not run the app.' }
} finally {
    $env:PYTHONPATH = $beforePythonPath
    $env:PIP_NO_INDEX = $beforeNoIndex
    $env:PIP_NO_INPUT = $beforeNoInput
    $env:PIP_DISABLE_PIP_VERSION_CHECK = $beforePipVersion
}
Write-Host 'Offline Python environment installed and smoke-tested without pip indexes.'
