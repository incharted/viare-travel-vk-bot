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
    param(
        [string]$ExplicitPython
    )

    if ($ExplicitPython) {
        $explicit = $ExplicitPython.Trim()
        if ($explicit) {
            if ($explicit -match "^(?i:py(?:\.exe)?)\s+(.+)$") {
                $py = Get-Command py -ErrorAction SilentlyContinue
                if ($py) {
                    $spec = New-PythonSpec -Executable $py.Source -PrefixArgs @($matches[1].Trim())
                    if (Test-PythonRuntime -Spec $spec) {
                        return $spec
                    }
                }
            }
            else {
                $spec = New-PythonSpec -Executable $explicit
                if (Test-PythonRuntime -Spec $spec) {
                    return $spec
                }
            }
        }
    }

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

    foreach ($candidateRoot in @(
        "$env:LocalAppData\Programs\Python",
        "$env:ProgramFiles\Python"
    )) {
        if (-not (Test-Path $candidateRoot)) {
            continue
        }

        $pythonExe = Get-ChildItem $candidateRoot -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName

        if ($pythonExe) {
            $candidate = New-PythonSpec -Executable $pythonExe
            if (Test-PythonRuntime -Spec $candidate) {
                return $candidate
            }
        }
    }

    return $null
}

function Save-LauncherSpec {
    param(
        [string]$Path,
        [PSCustomObject]$Spec
    )

    $payload = [PSCustomObject]@{
        executable = $Spec.Executable
        prefix_args = @($Spec.PrefixArgs)
    } | ConvertTo-Json -Depth 4

    Set-Content -Path $Path -Value $payload -Encoding UTF8
}

$projectRoot = Resolve-ProjectRoot
Set-Location $projectRoot

$launcherPath = Join-Path $projectRoot ".python_launcher.json"
$resolvedPython = Resolve-Python -ExplicitPython $PythonExe
if (-not $resolvedPython) {
    Write-Host "Python 3.11+ was not found on this PC." -ForegroundColor Red
    Write-Host "Install Python from https://www.python.org/downloads/windows/ and re-run this script." -ForegroundColor Yellow
    exit 1
}

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$venvSpec = New-PythonSpec -Executable $venvPython
$venvReady = (Test-Path $venvPython) -and (Test-PythonRuntime -Spec $venvSpec)

if (-not $venvReady) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    try {
        Invoke-Python -Spec $resolvedPython -Arguments @("-m", "venv", ".venv")
    }
    catch {
        Write-Host "Could not create .venv in this path. Switching to fallback runtime." -ForegroundColor Yellow
    }

    $venvReady = (Test-Path $venvPython) -and (Test-PythonRuntime -Spec $venvSpec)
}

$runtimeSpec = $null
$runtimeLabel = ""

if ($venvReady) {
    $runtimeSpec = $venvSpec
    $runtimeLabel = ".venv"
    Write-Host "Installing dependencies into .venv..." -ForegroundColor Cyan

    Invoke-Python -Spec $runtimeSpec -Arguments @("-m", "pip", "install", "--no-cache-dir", "--upgrade", "pip")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip in .venv."
    }

    Invoke-Python -Spec $runtimeSpec -Arguments @("-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements in .venv."
    }

    if (Test-Path $launcherPath) {
        Remove-Item $launcherPath -Force
    }
}
else {
    $runtimeSpec = $resolvedPython
    $runtimeLabel = "system python"

    Write-Host "Warning: .venv cannot be started from this path (often happens with OneDrive/Cyrillic paths)." -ForegroundColor Yellow
    Write-Host "Installing dependencies for current user profile..." -ForegroundColor Cyan

    Invoke-Python -Spec $runtimeSpec -Arguments @("-m", "pip", "install", "--user", "--no-cache-dir", "-r", "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements for system python."
    }

    Save-LauncherSpec -Path $launcherPath -Spec $runtimeSpec
}

if (-not (Test-ProjectImports -Spec $runtimeSpec)) {
    throw "Dependencies were not installed correctly (import check failed)."
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
Write-Host "Setup complete. Runtime: $runtimeLabel" -ForegroundColor Green
Write-Host "Run the bot with: .\scripts\run.ps1" -ForegroundColor Green
