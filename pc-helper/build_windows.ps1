param(
    [string]$ApkPath = "..\android\app\build\outputs\apk\debug\app-debug.apk"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$HelperDir = Join-Path $Root "pc-helper\qt6"
$DistDir = Join-Path $HelperDir "dist"
$BundleDir = Join-Path $Root "pc-helper\release"

Write-Host "MIBU PC Helper build" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH. Install Python 3.10+ first."
}

python -m pip install --upgrade pip
python -m pip install -r (Join-Path $HelperDir "requirements.txt") pyinstaller

if (Test-Path $DistDir) { Remove-Item $DistDir -Recurse -Force }
if (Test-Path $BundleDir) { Remove-Item $BundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $BundleDir | Out-Null

Push-Location $HelperDir
python -m PyInstaller --noconfirm --windowed --name "MIBU-PC-Helper" "mibu_pc_helper_final.py"
Pop-Location

Copy-Item (Join-Path $HelperDir "dist\MIBU-PC-Helper") $BundleDir -Recurse -Force

$BundleDist = Join-Path $BundleDir "MIBU-PC-Helper\dist"
New-Item -ItemType Directory -Path $BundleDist -Force | Out-Null

$ResolvedApk = Join-Path $Root $ApkPath
if (Test-Path $ResolvedApk) {
    Copy-Item $ResolvedApk (Join-Path $BundleDist "MIBU.apk") -Force
    Write-Host "Bundled APK: $ResolvedApk" -ForegroundColor Green
} else {
    Write-Warning "APK not found at $ResolvedApk. Build Android first or pass -ApkPath."
}

Write-Host "Release folder: $BundleDir" -ForegroundColor Green
