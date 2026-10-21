# Run on a connected, disposable Windows preparation machine.
# Deliberately downloads wheels; never invoke this on an offline workstation.
param(
    [Parameter(Mandatory=$true)][string]$Wheelhouse
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Prepare a Windows wheelhouse on Windows x64 with Python 3.11.'
}
$root = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path $root 'requirements.txt'
if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) {
    throw 'Repository requirements.txt missing.'
}
if ([IO.Path]::IsPathRooted($Wheelhouse) -eq $false) {
    throw 'Specify an absolute wheelhouse destination.'
}
if (Test-Path -LiteralPath $Wheelhouse) {
    throw 'Wheelhouse destination must be new and empty; existing data is never overwritten.'
}
$python = (Get-Command python -ErrorAction Stop).Source
& $python -c "import sys,struct; assert sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8, 'Requires 64-bit Python 3.11'"
if ($LASTEXITCODE -ne 0) { throw 'Wrong Windows Python interpreter.' }
New-Item -ItemType Directory -Path $Wheelhouse -ErrorAction Stop | Out-Null
$beforePythonPath = $env:PYTHONPATH
try {
    # This script is intentionally online. No downloads happen in the
    # install script that consumes these exact wheels and hashes.
    & $python -m pip --disable-pip-version-check download --only-binary=:all: --dest $Wheelhouse --requirement $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Wheel download failed; do not distribute partial wheelhouse.' }
    $env:PYTHONPATH = Join-Path $root 'src'
    & $python -m mcm_solarcheck.offline.wheelhouse create --wheelhouse $Wheelhouse --requirements $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Wheelhouse manifest creation failed.' }
    & $python -m mcm_solarcheck.offline.wheelhouse verify --wheelhouse $Wheelhouse --requirements $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Wheelhouse verification failed.' }
} finally {
    $env:PYTHONPATH = $beforePythonPath
}
Write-Host 'Prepared wheelhouse; transfer wheels, manifest and matching project source securely.'
Write-Host 'SHA256 checks detect changes relative to the manifest; this is not code signing.'
