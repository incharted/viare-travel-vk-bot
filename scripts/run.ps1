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

function New-PythonSpec {
    param(
        [string]$Executable,
        [string[]]$PrefixArgs = @()
    )

    return [PSCustomObject]@{
        Executable = $Executable
        PrefixArgs = @($PrefixArgs)
    }
}

function Invoke-Python {
    param(
        [PSCustomObject]$Spec,
        [string[]]$Arguments
    )

    if (-not $Spec -or -not $Spec.Executable) {
        throw "Python runtime specification is empty."
    }

    $safeExecutable = Resolve-ExecutablePath -Path $Spec.Executable
    $prefixArgs = @($Spec.PrefixArgs)
    & $safeExecutable @prefixArgs @Arguments
}

function Test-PythonRuntime {
    param(
        [PSCustomObject]$Spec
    )

    if (-not $Spec) {
        return $false
    }

    try {
        Invoke-Python -Spec $Spec -Arguments @("-c", "import sys; print(sys.version)") *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Test-ProjectImports {
    param(
        [PSCustomObject]$Spec
    )

    try {
        Invoke-Python -Spec $Spec -Arguments @("-c", "import vkbottle, dotenv, aiosqlite, openpyxl, reportlab") *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Resolve-Python {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        foreach ($version in @("-3.13", "-3.12", "-3.11", "-3")) {
            $candidate = New-PythonSpec -Executable $pyCommand.Source -PrefixArgs @($version)
            if (Test-PythonRuntime -Spec $candidate) {
                return $candidate
            }
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidate = New-PythonSpec -Executable $pythonCommand.Source
        if (Test-PythonRuntime -Spec $candidate) {
            return $candidate
        }
    }

    return $null
}

function Load-LauncherSpec {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        $raw = Get-Content $Path -Raw | ConvertFrom-Json
        if (-not $raw.executable) {
            return $null
        }

        $prefixArgs = @()
        if ($raw.prefix_args) {
            $prefixArgs = @($raw.prefix_args)
        }

        return New-PythonSpec -Executable ([string]$raw.executable) -PrefixArgs $prefixArgs
    }
    catch {
        return $null
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$launcherPath = Join-Path $projectRoot ".python_launcher.json"
$venvSpec = New-PythonSpec -Executable (Join-Path $projectRoot ".venv\Scripts\python.exe")
$runtimeSpec = $null

if ((Test-Path $venvSpec.Executable) -and (Test-PythonRuntime -Spec $venvSpec)) {
    $runtimeSpec = $venvSpec
}

if (-not $runtimeSpec) {
    $savedSpec = Load-LauncherSpec -Path $launcherPath
    if ($savedSpec -and (Test-PythonRuntime -Spec $savedSpec)) {
        $runtimeSpec = $savedSpec
    }
}

if (-not $runtimeSpec) {
    $resolved = Resolve-Python
    if ($resolved -and (Test-PythonRuntime -Spec $resolved)) {
        $runtimeSpec = $resolved
    }
}

if (-not $runtimeSpec) {
    Write-Host "No working Python runtime found." -ForegroundColor Red
    Write-Host "Run .\scripts\setup.ps1 first, or install Python 3.11+." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-ProjectImports -Spec $runtimeSpec)) {
    Write-Host "Dependencies are missing for the selected Python runtime." -ForegroundColor Red
    Write-Host "Run .\scripts\setup.ps1 first." -ForegroundColor Yellow
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

Write-Host "Starting bot..." -ForegroundColor Cyan
Invoke-Python -Spec $runtimeSpec -Arguments @("main.py")
