# Opt-in, private Windows 10 acceptance of the M3T original ZIP -> project bridge.
# Only audits bytes/SQLite in READ-ONLY mode; never imports, installs or trains.
# Call once BEFORE the GUI import, then again with -Database and -ProjectId.
param(
    [Parameter(Mandatory = $true)][string]$ThermalZip,
    [Parameter(Mandatory = $true)][string]$RgbZip,
    [string]$Database,
    [string]$ProjectId,
    [switch]$IncludeUnpairedThermal,
    [int]$ExpectedThermal = 160,
    [int]$ExpectedRgb = 33,
    [int]$ExpectedMetadataPairs = 33
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This validation script requires a real Windows 10 workstation.'
}
$caption = (Get-CimInstance -ClassName Win32_OperatingSystem).Caption
if ($caption -notmatch 'Windows 10') {
    throw 'This validation script requires a real Windows 10 workstation.'
}
if ([string]::IsNullOrWhiteSpace($Database) -ne [string]::IsNullOrWhiteSpace($ProjectId)) {
    throw 'Database and ProjectId must both be provided for post-import verification.'
}
if ($IncludeUnpairedThermal -and [string]::IsNullOrWhiteSpace($Database)) {
    throw 'The unpaired Thermal choice can only be checked after GUI import.'
}
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Local Python virtualenv missing. See INSTALLATION.md.'
}
$beforePythonPath = $env:PYTHONPATH
$beforeBytecode = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Push-Location $root
    try {
        $cli = @(
            '-m', 'mcm_solarcheck.offline.zip_acceptance_cli',
            '--thermal-zip', $ThermalZip,
            '--rgb-zip', $RgbZip,
            '--expected-thermal', [string]$ExpectedThermal,
            '--expected-rgb', [string]$ExpectedRgb,
            '--expected-metadata-pairs', [string]$ExpectedMetadataPairs
        )
        if (-not [string]::IsNullOrWhiteSpace($Database)) {
            $cli += @('--database', $Database, '--project-id', $ProjectId)
        }
        if ($IncludeUnpairedThermal) {
            $cli += '--include-unpaired-thermal'
        }
        & $python @cli
        if ($LASTEXITCODE -ne 0) {
            throw 'The private ZIP/project acceptance failed (no private paths are logged).'
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:PYTHONPATH = $beforePythonPath
    $env:PYTHONDONTWRITEBYTECODE = $beforeBytecode
}
Write-Host 'Private read-only DJI ZIP acceptance completed successfully.'
