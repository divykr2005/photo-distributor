# Run this script in PowerShell AS ADMINISTRATOR
# It installs pgvector for PostgreSQL 18 on Windows

$ErrorActionPreference = "Stop"
$PGROOT = "C:\Program Files\PostgreSQL\18"

Write-Host "=== Step 1: Install VS Build Tools (C++ workload) ===" -ForegroundColor Cyan

# Check if nmake already exists
$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$hasVS = $false
if (Test-Path $vsWhere) {
    $installPath = & $vsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
    if ($installPath) { $hasVS = $true }
}

if (-not $hasVS) {
    Write-Host "Downloading VS Build Tools installer..."
    $installerUrl = "https://aka.ms/vs/17/release/vs_BuildTools.exe"
    $installerPath = "$env:TEMP\vs_BuildTools.exe"
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    
    Write-Host "Installing C++ Build Tools (this takes a few minutes)..."
    Start-Process -FilePath $installerPath -ArgumentList `
        "--quiet", "--wait", "--norestart", `
        "--add", "Microsoft.VisualStudio.Workload.VCTools", `
        "--includeRecommended" `
        -Wait -NoNewWindow
    
    Write-Host "VS Build Tools installed." -ForegroundColor Green
} else {
    Write-Host "VS Build Tools already installed." -ForegroundColor Green
}

Write-Host "`n=== Step 2: Clone pgvector ===" -ForegroundColor Cyan
$buildDir = "$env:TEMP\pgvector_build"
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
git clone https://github.com/pgvector/pgvector.git $buildDir
Set-Location $buildDir

Write-Host "`n=== Step 3: Build & Install ===" -ForegroundColor Cyan

# Find vcvars64.bat
$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = & $vsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $vcvars)) {
    Write-Error "Could not find vcvars64.bat. VS Build Tools may not have installed correctly."
    exit 1
}

# Build using cmd (nmake needs the VS environment)
cmd /c "`"$vcvars`" && set `"PGROOT=$PGROOT`" && nmake /F Makefile.win && nmake /F Makefile.win install"

Write-Host "`n=== Step 4: Verify ===" -ForegroundColor Cyan
if (Test-Path "$PGROOT\share\extension\vector.control") {
    Write-Host "pgvector installed successfully!" -ForegroundColor Green
} else {
    Write-Error "Installation failed - vector.control not found"
    exit 1
}

Write-Host "`nDone! Now run 'alembic upgrade head' from your backend directory." -ForegroundColor Yellow
