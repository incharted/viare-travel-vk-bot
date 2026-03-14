param(
    [Parameter(Mandatory = $true)]
    [string]$VkId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($VkId -notmatch '^\d+$') {
    throw "VkId must contain digits only."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([string[]](Get-Content ".env"))

$adminIndex = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^ADMIN_IDS=') {
        $adminIndex = $i
        break
    }
}

$ids = [System.Collections.Generic.HashSet[string]]::new()
if ($adminIndex -ge 0) {
    $existingValue = ($lines[$adminIndex] -replace '^ADMIN_IDS=', '').Trim()
    foreach ($item in ($existingValue -split ',')) {
        $value = $item.Trim()
        if ($value -match '^\d+$') {
            [void]$ids.Add($value)
        }
    }
}

[void]$ids.Add($VkId)
$newValue = ($ids | Sort-Object) -join ","

if ($adminIndex -ge 0) {
    $lines[$adminIndex] = "ADMIN_IDS=$newValue"
}
else {
    $lines.Add("ADMIN_IDS=$newValue")
}

Set-Content ".env" $lines -Encoding UTF8
Write-Host "Updated ADMIN_IDS in .env: $newValue" -ForegroundColor Green
