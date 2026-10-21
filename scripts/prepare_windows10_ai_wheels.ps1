# Separates, absichtlich ONLINE ausgeführtes Vorbereitungsskript.
# Torch/TorchVision werden nicht Teil der Standardinstallation.
param([Parameter(Mandatory=$true)][string]$Wheelhouse)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Windows x64 preparation system required.'
}
if (-not [IO.Path]::IsPathRooted($Wheelhouse)) {
    throw 'An absolute destination is required.'
}
if (Test-Path -LiteralPath $Wheelhouse) {
    throw 'Wheelhouse must be new: no replacing previously checked packages.'
}
$root = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path $root 'requirements-offline-ai.txt'
$python = (Get-Command python -ErrorAction Stop).Source
& $python -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8"
if ($LASTEXITCODE -ne 0) { throw '64-bit Python 3.11 required.' }
New-Item -ItemType Directory -Path $Wheelhouse | Out-Null
$beforePythonPath = $env:PYTHONPATH
try {
    # Explicitly connected system only. Never executed by SolarCheck startup.
    & $python -m pip --disable-pip-version-check download --only-binary=:all: --dest $Wheelhouse --requirement $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Incomplete optional OSS AI wheelhouse; do not transfer.' }
    $env:PYTHONPATH = Join-Path $root 'src'
    & $python -m mcm_solarcheck.offline.wheelhouse create --wheelhouse $Wheelhouse --requirements $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Could not sign inventory with local checksums.' }
    & $python -m mcm_solarcheck.offline.wheelhouse verify --wheelhouse $Wheelhouse --requirements $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Wheel inventory hash mismatch.' }
} finally {
    $env:PYTHONPATH = $beforePythonPath
}
Write-Host 'Optional OSS AI wheels ready for transfer. SHA-256 manifest is not a signature.'
