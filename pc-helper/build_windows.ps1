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
python -m PyInstaller --noconfirm --windowed --name "MIBU-PC-Helper" --hidden-import PySide6.QtMultimedia "mibu_pc_helper_final.py"
Pop-Location

Copy-Item (Join-Path $HelperDir "dist\MIBU-PC-Helper") $BundleDir -Recurse -Force

$BundleApp = Join-Path $BundleDir "MIBU-PC-Helper"
$BundleDist = Join-Path $BundleApp "dist"
New-Item -ItemType Directory -Path $BundleDist -Force | Out-Null

$ResolvedApk = Join-Path $Root $ApkPath
if (Test-Path $ResolvedApk) {
    Copy-Item $ResolvedApk (Join-Path $BundleDist "MIBU.apk") -Force
    Write-Host "Bundled APK: $ResolvedApk" -ForegroundColor Green
} else {
    Write-Warning "APK not found at $ResolvedApk. Build Android first or pass -ApkPath."
}

$ResourceRoot = Join-Path $Root "resources"
if (Test-Path $ResourceRoot) {
    $BundleResources = Join-Path $BundleApp "resources"
    Copy-Item $ResourceRoot $BundleResources -Recurse -Force
    Write-Host "Bundled resources: $ResourceRoot" -ForegroundColor Green
} else {
    Write-Warning "resources folder not found. The helper will use code fallback UI until resources are restored."
}

$AudioRoots = @(
    (Join-Path $Root "resources\expected ui"),
    (Join-Path $Root "resources\expected ui\android"),
    (Join-Path $Root "resources")
)
$AudioNames = @(
    "TTG_v4_clean_connected_success.wav",
    "TTG_v4_clean_speaker_turn_on.wav"
)
foreach ($name in $AudioNames) {
    $found = $false
    foreach ($dir in $AudioRoots) {
        $candidate = Join-Path $dir $name
        if (Test-Path $candidate) {
            Copy-Item $candidate (Join-Path $BundleDist $name) -Force
            Write-Host "Bundled audio: $candidate" -ForegroundColor Green
            $found = $true
            break
        }
    }
    if (-not $found) {
        Write-Warning "Audio not found: $name"
    }
}

Write-Host "Release folder: $BundleDir" -ForegroundColor Green
