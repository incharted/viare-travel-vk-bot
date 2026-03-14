param(
    [string]$PythonExe = ""
)

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

function Resolve-ProjectRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Resolve-Python {
    param(
        [string]$ExplicitPython
    )

    if ($ExplicitPython) {
        return $ExplicitPython
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        foreach ($version in @("-3.13", "-3.12", "-3.11", "-3")) {
            try {
                & $pyCommand.Source $version -c "import sys; print(sys.executable)" 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    return "$($pyCommand.Source) $version"
                }
            }
            catch {
            }
        }
    }

    foreach ($candidate in @(
        "$env:LocalAppData\Programs\Python",
        "$env:ProgramFiles\Python"
    )) {
        if (-not (Test-Path $candidate)) {
            continue
        }

        $pythonExe = Get-ChildItem $candidate -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName

        if ($pythonExe) {
            return $pythonExe
        }
    }

    return $null
}

function Invoke-Python {
    param(
        [string]$PythonCommand,
        [string[]]$Arguments
    )

    if ($PythonCommand -like "* *") {
        $parts = $PythonCommand -split " ", 2
        $safeExecutable = Resolve-ExecutablePath -Path $parts[0]
        & $safeExecutable $parts[1] @Arguments
        return
    }

    $safeExecutable = Resolve-ExecutablePath -Path $PythonCommand
    & $safeExecutable @Arguments
}

$projectRoot = Resolve-ProjectRoot
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$safeVenvPython = Resolve-ExecutablePath -Path $venvPython
if (-not (Test-Path $venvPython)) {
    $resolvedPython = Resolve-Python -ExplicitPython $PythonExe
    if (-not $resolvedPython) {
        Write-Host "Python 3.11+ was not found on this PC." -ForegroundColor Red
        Write-Host "Install Python from https://www.python.org/downloads/windows/ and re-run this script." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    Invoke-Python -PythonCommand $resolvedPython -Arguments @("-m", "venv", ".venv")
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $safeVenvPython -m pip install --no-cache-dir --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}

& $safeVenvPython -m pip install --no-cache-dir -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install project requirements."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Green
}

$envContent = Get-Content ".env" -Raw
$tokenConfigured = $envContent -match "(?m)^VK_TOKEN=(?!your_token_here$).+"
$adminConfigured = $envContent -match "(?m)^ADMIN_IDS=\d+(,\d+)*$"

if (-not $tokenConfigured) {
    Write-Host "VK token is not configured yet. Open .env and set VK_TOKEN." -ForegroundColor Yellow
}

if (-not $adminConfigured) {
    Write-Host "ADMIN_IDS is empty. After you know your VK ID, run:" -ForegroundColor Yellow
    Write-Host ".\scripts\set-admin.ps1 -VkId 123456789" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run the bot with: .\scripts\run.ps1" -ForegroundColor Green
