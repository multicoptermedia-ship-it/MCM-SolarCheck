# Start the normal offline desktop using the local preinstalled virtualenv.
# No package installation, updates, licensing checks or network calls here.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Offline Python environment not found. See INSTALLATION.md.'
}
$beforePythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    Push-Location $root
    try {
        & $python -m mcm_solarcheck.offline
        if ($LASTEXITCODE -ne 0) { throw 'MCM-SolarCheck offline desktop failed.' }
    } finally {
        Pop-Location
    }
} finally {
    $env:PYTHONPATH = $beforePythonPath
}
