# Online preparation ONLY; never executed by the offline SolarCheck application.
# Download publicly published Raptor Maps archive at its PINNED Git commit.
# The local importer verifies the precise upstream Git blob before extraction.
param([Parameter(Mandatory=$true)][string]$DestinationDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not [IO.Path]::IsPathRooted($DestinationDirectory)) {
    throw 'Use an absolute path for a new preparation folder.'
}
if (Test-Path -LiteralPath $DestinationDirectory) {
    throw 'Existing download directory must never be overwritten.'
}
New-Item -Path $DestinationDirectory -ItemType Directory -ErrorAction Stop | Out-Null
$target = Join-Path $DestinationDirectory '2020-02-14_InfraredSolarModules.zip'
$upstream = 'https://raw.githubusercontent.com/RaptorMaps/InfraredSolarModules/88e2d1febbcefe401c17ec80b8973f36a02a1653/2020-02-14_InfraredSolarModules.zip'
try {
    Invoke-WebRequest -UseBasicParsing -Uri $upstream -OutFile $target -ErrorAction Stop
    $archive = Get-Item -LiteralPath $target
    if ($archive.Length -ne 15495990) {
        throw 'Downloaded file does not match official 2020-02-14 ZIP length.'
    }
} catch {
    Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
    throw
}
Write-Host 'Archive downloaded to preparation computer ONLY.'
Write-Host 'Transfer archive by trusted removable media, then run the local offline importer.'
Write-Host 'The offline importer verifies the pinned Git blob SHA-1 and publishes SHA-256.'
