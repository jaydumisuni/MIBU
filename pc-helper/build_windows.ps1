param(
    [string]$ApkPath = "android\app\build\outputs\apk\debug\app-debug.apk"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$HelperDir = Join-Path $Root "pc-helper\qt6"
$DistDir = Join-Path $HelperDir "dist"
$BundleDir = Join-Path $Root "pc-helper\release"
$ResolvedApk = Join-Path $Root $ApkPath

Write-Host "MIBU PC Helper build" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH. Install Python 3.10+ first."
}

function Remove-SafeDir([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    try {
        Remove-Item $Path -Recurse -Force -ErrorAction Stop
    } catch {
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $renamed = "$Path.locked_$stamp"
        Write-Warning "Could not remove $Path, probably because the helper is still running or a DLL is locked. Renaming old folder to $renamed"
        Rename-Item $Path $renamed -ErrorAction Stop
    }
}

python -m pip install --upgrade pip
python -m pip install -r (Join-Path $HelperDir "requirements.txt") pyinstaller

if (-not (Test-Path $ResolvedApk)) {
    $Gradle = Get-Command gradle -ErrorAction SilentlyContinue
    if ($Gradle) {
        Write-Host "Android APK missing. Building it first..." -ForegroundColor Cyan
        Push-Location $Root
        gradle :android:app:assembleDebug
        Pop-Location
    }
}
if (-not (Test-Path $ResolvedApk)) {
    throw "Android APK is required for a complete MIBU release but was not found at $ResolvedApk. Build Android first with Gradle or pass -ApkPath."
}

Write-Host "Rendering deterministic hotspot UI assets..." -ForegroundColor Cyan
python (Join-Path $HelperDir "render_svg_assets.py")

$RequiredUi = @(
    (Join-Path $Root "resources\expected ui\pc\01_pc_main_four_button_workflow.png"),
    (Join-Path $Root "resources\expected ui\pc\02_popup_device_check_guide.png"),
    (Join-Path $Root "resources\expected ui\pc\03_popup_install_apk.png"),
    (Join-Path $Root "resources\expected ui\pc\04_popup_login_get_token.png"),
    (Join-Path $Root "resources\expected ui\pc\05_popup_phone_guide.png")
)
foreach ($asset in $RequiredUi) {
    if (-not (Test-Path $asset)) { throw "Required hotspot UI asset was not rendered: $asset" }
}
Write-Host "Hotspot UI assets verified." -ForegroundColor Green

$env:QT_QPA_PLATFORM = "offscreen"
Push-Location $HelperDir
python -c "import mibu_pc_helper_v2; assert mibu_pc_helper_v2.next_target().tzinfo is not None; print('MIBU v2 import/math smoke check passed')"
Pop-Location
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue

Remove-SafeDir $DistDir
Remove-SafeDir $BundleDir
New-Item -ItemType Directory -Path $BundleDir | Out-Null

Push-Location $HelperDir
python -m PyInstaller --noconfirm --windowed --name "MIBU-PC-Helper" --hidden-import PySide6.QtMultimedia "mibu_pc_helper_v2.py"
Pop-Location

Copy-Item (Join-Path $HelperDir "dist\MIBU-PC-Helper") $BundleDir -Recurse -Force
$BundleApp = Join-Path $BundleDir "MIBU-PC-Helper"
$BundleDist = Join-Path $BundleApp "dist"
New-Item -ItemType Directory -Path $BundleDist -Force | Out-Null
Copy-Item $ResolvedApk (Join-Path $BundleDist "MIBU.apk") -Force
Write-Host "Bundled APK: $ResolvedApk" -ForegroundColor Green

$ResourceRoot = Join-Path $Root "resources"
if (-not (Test-Path $ResourceRoot)) { throw "resources folder not found. Hotspot UI cannot be bundled." }
$BundleResources = Join-Path $BundleApp "resources"
Copy-Item $ResourceRoot $BundleResources -Recurse -Force
Write-Host "Bundled resources: $ResourceRoot" -ForegroundColor Green

foreach ($asset in $RequiredUi) {
    $relative = $asset.Substring($ResourceRoot.Length).TrimStart('\')
    $bundled = Join-Path $BundleResources $relative
    if (-not (Test-Path $bundled)) { throw "Required hotspot UI asset missing from release bundle: $bundled" }
}
if (-not (Test-Path (Join-Path $BundleDist "MIBU.apk"))) { throw "MIBU.apk missing from final release bundle." }
Write-Host "Release APK and hotspot assets verified." -ForegroundColor Green

$AudioRoots = @(
    (Join-Path $Root "resources\expected ui"),
    (Join-Path $Root "resources\expected ui\android"),
    (Join-Path $Root "resources")
)
foreach ($name in @("TTG_v4_clean_connected_success.wav", "TTG_v4_clean_speaker_turn_on.wav")) {
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
    if (-not $found) { Write-Warning "Optional audio not found: $name" }
}

Write-Host "Release folder: $BundleDir" -ForegroundColor Green
