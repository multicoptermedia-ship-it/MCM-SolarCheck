# Local Windows 10 acceptance test: zero dependency downloads or updates.
# Run in PowerShell from the checked-out source tree after the virtualenv exists.
param([switch]$IncludeTests)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This validation script is only for Windows 10.'
}
$caption = (Get-CimInstance -ClassName Win32_OperatingSystem).Caption
if ($caption -notmatch 'Windows 10') {
    throw 'This acceptance script requires a real Windows 10 workstation.'
}
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Local virtualenv missing. Set up the offline Python environment first.'
}
$beforePythonPath = $env:PYTHONPATH
$beforeQtPlatform = $env:QT_QPA_PLATFORM
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $env:QT_QPA_PLATFORM = 'offscreen'
    Push-Location $root
    try {
        & $python -m mcm_solarcheck.offline.windows_smoke --headless
        if ($LASTEXITCODE -ne 0) { throw 'Offline Windows 10 smoke check failed.' }
        if ($IncludeTests) {
            & $python -m pytest -q tests/test_windows_admin_native.py tests/test_windows_offline_startup.py tests/test_offline_admin_password_rotation_gui.py
            if ($LASTEXITCODE -ne 0) { throw 'Windows 10 regression tests failed.' }
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:PYTHONPATH = $beforePythonPath
    $env:QT_QPA_PLATFORM = $beforeQtPlatform
}
Write-Host 'Windows 10 offline smoke check complete; no real project was modified.'
