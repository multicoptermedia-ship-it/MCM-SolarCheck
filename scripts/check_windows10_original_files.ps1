# Opt-in Windows 10 original DJI-file acceptance. ZIP is never required.
# Zero installation, no GUI automation, no database writes or network.
# Can be called with one/multiple SourceFolders or individual OriginalFiles.
param(
    [string[]]$SourceFolders = @(),
    [string[]]$OriginalFiles = @(),
    [string]$Database,
    [string]$ProjectId,
    [int]$ExpectedThermal = 160,
    [int]$ExpectedRgb = 33,
    [int]$ExpectedMetadataPairs = 33
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    (Get-CimInstance -ClassName Win32_OperatingSystem).Caption -notmatch 'Windows 10') {
    throw 'This pilot check must run on a real Windows 10 workstation.'
}
if (($SourceFolders.Count + $OriginalFiles.Count) -eq 0) {
    throw 'Supply at least one original-image source folder or selected file.'
}
if ([string]::IsNullOrWhiteSpace($Database) -ne [string]::IsNullOrWhiteSpace($ProjectId)) {
    throw 'Database and ProjectId are required together for post-import checking.'
}
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Offline Python environment missing. See INSTALLATION.md.'
}
$previousPath = $env:PYTHONPATH
$previousBytecode = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Push-Location $root
    try {
        $argsCli = @(
            '-m', 'mcm_solarcheck.offline.original_files_acceptance_cli',
            '--expected-thermal', [string]$ExpectedThermal,
            '--expected-rgb', [string]$ExpectedRgb,
            '--expected-metadata-pairs', [string]$ExpectedMetadataPairs
        )
        foreach ($dir in $SourceFolders) { $argsCli += @('--source-folder', $dir) }
        foreach ($file in $OriginalFiles) { $argsCli += @('--original-file', $file) }
        if (-not [string]::IsNullOrWhiteSpace($Database)) {
            $argsCli += @('--database', $Database, '--project-id', $ProjectId)
        }
        & $python @argsCli
        if ($LASTEXITCODE -ne 0) {
            throw 'The private original-image acceptance failed (no confidential details logged).'
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:PYTHONPATH = $previousPath
    $env:PYTHONDONTWRITEBYTECODE = $previousBytecode
}
Write-Host 'Unpacked DJI original acceptance finished; no project was changed.'
