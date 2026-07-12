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

function Resolve-Gradle {
    $command = Get-Command gradle -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidates = @(
        "D:\mibu-build-tools\gradle\bin\gradle.bat",
        "D:\mibu-build-tools\gradle-8.10.2\bin\gradle.bat",
        (Join-Path $Root "gradlew.bat")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Resolve-AndroidSdk {
    foreach ($candidate in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, "D:\mibu-build-tools\android-sdk")) {
        if ($candidate -and (Test-Path $candidate)) { return (Resolve-Path $candidate).Path }
    }
    return $null
}

python -m pip install --upgrade pip
python -m pip install -r (Join-Path $HelperDir "requirements.txt") pyinstaller

if (-not (Test-Path $ResolvedApk)) {
    $GradlePath = Resolve-Gradle
    $AndroidSdk = Resolve-AndroidSdk
    if (-not $GradlePath) {
        throw "Android APK is missing and Gradle was not found. Expected gradle in PATH, D:\mibu-build-tools\gradle\bin\gradle.bat, D:\mibu-build-tools\gradle-8.10.2\bin\gradle.bat, or gradlew.bat in the repo."
    }
    if (-not $AndroidSdk) {
        throw "Android APK is missing and Android SDK was not found. Set ANDROID_SDK_ROOT/ANDROID_HOME or install it at D:\mibu-build-tools\android-sdk."
    }

    $LocalProperties = Join-Path $Root "local.properties"
    $EscapedSdk = $AndroidSdk.Replace('\', '\\')
    Set-Content -Path $LocalProperties -Value "sdk.dir=$EscapedSdk" -Encoding ASCII
    Write-Host "Android APK missing. Building with $GradlePath" -ForegroundColor Cyan
    Write-Host "Android SDK: $AndroidSdk" -ForegroundColor Cyan
    Push-Location $Root
    try {
        & $GradlePath :android:app:testDebugUnitTest :android:app:assembleDebug --stacktrace
        if ($LASTEXITCODE -ne 0) { throw "Android Gradle build failed with exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
}
if (-not (Test-Path $ResolvedApk)) {
    throw "Android APK is required for a complete MIBU release but was not created at $ResolvedApk."
}

Write-Host "Rendering deterministic hotspot UI assets..." -ForegroundColor Cyan
python (Join-Path $HelperDir "validate_ui_contract.py")
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
    if ((Get-Item $asset).Length -le 0) { throw "Required hotspot UI asset is empty: $asset" }
}
Write-Host "Hotspot UI assets verified." -ForegroundColor Green

$env:QT_QPA_PLATFORM = "offscreen"
Push-Location $HelperDir
try {
    python -c "import mibu_pc_helper_v2; assert mibu_pc_helper_v2.next_target().tzinfo is not None; print('MIBU v2 import/math smoke check passed')"
    if ($LASTEXITCODE -ne 0) { throw "MIBU v2 source smoke check failed" }
} finally {
    Pop-Location
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
}

Remove-SafeDir $DistDir
Remove-SafeDir $BundleDir
New-Item -ItemType Directory -Path $BundleDir | Out-Null

Push-Location $HelperDir
try {
    python -m PyInstaller --noconfirm --windowed --name "MIBU-PC-Helper" --hidden-import PySide6.QtMultimedia "mibu_pc_helper_v2.py"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

$BuiltHelper = Join-Path $HelperDir "dist\MIBU-PC-Helper"
if (-not (Test-Path $BuiltHelper)) { throw "PyInstaller output folder missing: $BuiltHelper" }
Copy-Item $BuiltHelper $BundleDir -Recurse -Force
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
    if ((Get-Item $bundled).Length -le 0) { throw "Bundled hotspot UI asset is empty: $bundled" }
}
$BundledApk = Join-Path $BundleDist "MIBU.apk"
$BundledExe = Join-Path $BundleApp "MIBU-PC-Helper.exe"
if (-not (Test-Path $BundledApk) -or (Get-Item $BundledApk).Length -le 0) { throw "MIBU.apk missing or empty in final release bundle." }
if (-not (Test-Path $BundledExe) -or (Get-Item $BundledExe).Length -le 0) { throw "MIBU-PC-Helper.exe missing or empty in final release bundle." }
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
