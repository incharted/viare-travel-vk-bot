param(
    [switch]$ResetDatabase
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "Cleaning runtime cache and temp files..." -ForegroundColor Cyan

# Remove local python cache files from project sources (venv is ignored).
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "*\.venv\*" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Get-ChildItem -Recurse -File -Include *.pyc,*.pyo -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike "*\.venv\*" } |
    Remove-Item -Force -ErrorAction SilentlyContinue

# Remove logs/lock.
foreach ($path in @("data\bot.log", "data\bot.log.1", "data\bot.lock")) {
    if (Test-Path $path) {
        Remove-Item $path -Force -ErrorAction SilentlyContinue
    }
}

# Remove temporary exports.
if (Test-Path "data\exports") {
    Get-ChildItem "data\exports" -File -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

if ($ResetDatabase) {
    if (Test-Path "data\bot.sqlite3") {
        Remove-Item "data\bot.sqlite3" -Force
        Write-Host "Database removed: data\bot.sqlite3" -ForegroundColor Yellow
    }
}

Write-Host "Cleanup complete." -ForegroundColor Green
