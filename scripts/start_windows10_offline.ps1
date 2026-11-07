# Start the offline desktop using an already installed Python environment.
# No package installation, updates, licensing checks or network calls here.
param(
    [string]$PythonExe,
    [string]$DatabasePath,
    [switch]$UseExistingProject
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Test-SolarCheckPython([string]$Candidate) {
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) { return $false }
    try {
        & $Candidate -c 'import sys; import PySide6, numpy, cv2, rasterio, pyproj, PIL, piexif, odf, docx, reportlab; sys.exit(0 if sys.version_info >= (3,11) else 3)' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Select-SolarCheckFile([string]$Title, [string]$Filter, [string]$InitialFile) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    try {
        $picker.Title = $Title
        $picker.Filter = $Filter
        $picker.CheckFileExists = $true
        if ($InitialFile -and (Test-Path -LiteralPath $InitialFile -PathType Leaf)) {
            $picker.FileName = $InitialFile
        }
        if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
            throw 'Start abgebrochen. Vorhandenes Projekt unveraendert.'
        }
        return $picker.FileName
    } finally { $picker.Dispose() }
}

if ($UseExistingProject -and -not $DatabasePath) {
    $defaultDatabase = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'MCM-SolarCheck\solarcheck.sqlite3'
    $DatabasePath = Select-SolarCheckFile 'Vorhandene SolarCheck-Projektdatei' 'SolarCheck SQLite (*.sqlite3;*.sqlite;*.db)|*.sqlite3;*.sqlite;*.db' $defaultDatabase
}
if ($DatabasePath -and -not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
    throw 'Vorhandene Projektdatei fehlt. Es wird keine neue Datenbank angelegt.'
}

if ($PythonExe) {
    if (-not (Test-SolarCheckPython $PythonExe)) {
        throw 'Diese Python-Umgebung hat nicht die vorhandenen SolarCheck-Abhaengigkeiten. Es wird nichts installiert.'
    }
} else {
    $candidates = @(Join-Path $root '.venv\Scripts\python.exe')
    if ($UseExistingProject) {
        if ($env:VIRTUAL_ENV) { $candidates += Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe' }
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notmatch 'WindowsApps') { $candidates += $command.Source }
    }
    foreach ($candidate in $candidates) {
        if (Test-SolarCheckPython $candidate) { $PythonExe = $candidate; break }
    }
    if (-not $PythonExe -and $UseExistingProject) {
        $PythonExe = Select-SolarCheckFile 'Bisherige Python-Programmdatei (z.B. alte .venv\Scripts\python.exe)' 'Python (python.exe)|python.exe' ''
        if (-not (Test-SolarCheckPython $PythonExe)) {
            throw 'SolarCheck-Abhaengigkeiten fehlen in dieser Umgebung. Es wird nichts installiert.'
        }
    }
    if (-not $PythonExe) { throw 'Offline Python environment not found. See INSTALLATION.md.' }
}

$arguments = @('-m', 'mcm_solarcheck.offline')
if ($DatabasePath) { $arguments += @('--existing-database', $DatabasePath) }
$beforePythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    Push-Location -LiteralPath $root
    try {
        & $PythonExe @arguments
        if ($LASTEXITCODE -ne 0) { throw 'MCM-SolarCheck offline desktop failed.' }
    } finally {
        Pop-Location
    }
} finally {
    $env:PYTHONPATH = $beforePythonPath
}
