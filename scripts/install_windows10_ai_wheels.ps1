# Optional Windows 10 KI-Backend-Installation NUR aus lokalem Wheelhouse.
# No cloud, no pip indexes, no pre-trained weights, no OS/package updater.
param([Parameter(Mandatory=$true)][string]$Wheelhouse)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Windows 10 target required.'
}
if (-not [IO.Path]::IsPathRooted($Wheelhouse) -or -not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
    throw 'Existing absolute wheelhouse required.'
}
$root = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path $root 'requirements-offline-ai.txt'
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'First provision the normal offline .venv; never reinstall it silently.'
}
$beforePythonPath = $env:PYTHONPATH
$beforeNoIndex = $env:PIP_NO_INDEX
$beforeNoInput = $env:PIP_NO_INPUT
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $env:PIP_NO_INDEX = '1'
    $env:PIP_NO_INPUT = '1'
    & $python -m mcm_solarcheck.offline.wheelhouse verify --wheelhouse $Wheelhouse --requirements $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Integrity verification failed before optional install.' }
    & $python -m pip --disable-pip-version-check install --no-index --only-binary=:all: --find-links $Wheelhouse --requirement $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Offline AI installation failed; inspect the local environment.' }
    & $python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Package dependency conflict after installation.' }
    & $python -c "import torch,torchvision; from torchvision.models import resnet18; model=resnet18(weights=None,num_classes=2); assert model.fc.out_features==2"
    if ($LASTEXITCODE -ne 0) { throw 'Local OSS backend import/architecture check failed.' }
} finally {
    $env:PYTHONPATH = $beforePythonPath
    $env:PIP_NO_INDEX = $beforeNoIndex
    $env:PIP_NO_INPUT = $beforeNoInput
}
Write-Host 'Optional local OSS backend ready. No model was downloaded or trained.'
