Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ExecutablePath {
    param(
        [string]$Path
    )

    try {
        $shortPath = cmd /c "for %I in (""$Path"") do @echo %~sI" 2>$null
        if ($LASTEXITCODE -eq 0 -and $shortPath) {
            return $shortPath.Trim()
        }
    }
    catch {
    }

    return $Path
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$safeVenvPython = Resolve-ExecutablePath -Path $venvPython
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment was not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host ".env is missing. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

$envContent = Get-Content ".env" -Raw
if (-not ($envContent -match "(?m)^VK_TOKEN=(?!your_token_here$).+")) {
    Write-Host "VK_TOKEN is empty in .env. Add the community token and try again." -ForegroundColor Red
    exit 1
}

if (-not ($envContent -match "(?m)^ADMIN_IDS=\d+(,\d+)*$")) {
    Write-Host "ADMIN_IDS is empty. You can still run the bot, but admin commands will stay locked." -ForegroundColor Yellow
}

& $safeVenvPython "main.py"
