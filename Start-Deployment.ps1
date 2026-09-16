if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Set-Location $PSScriptRoot
Write-Host "Building Docker containers..." -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build

Write-Host "Deployment started. Tailing logs (Press Ctrl+C to stop tailing)..." -ForegroundColor Yellow
docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f
