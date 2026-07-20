param(
    [string]$ApkPath = "android\app\build\outputs\apk\debug\app-debug.apk",
    [switch]$UseExistingApk
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$HelperDir = Join-Path $Root "pc-helper\qt6"
$DistDir = Join-Path $HelperDir "dist"
$BuildDir = Join-Path $HelperDir "build"
$BundleDir = Join-Path $Root "pc-helper\release"
$ResolvedApk = Join-Path $Root $ApkPath
$RequiredPlatformTools = @("adb.exe", "fastboot.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll")

Write-Host "MIBU PC Helper build" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host "APK mode: $(if ($UseExistingApk) { 'explicit prebuilt artifact' } else { 'rebuild from current Android source' })"

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
    foreach ($candidate in @(
        "D:\mibu-build-tools\gradle\bin\gradle.bat",
        "D:\mibu-build-tools\gradle\gradle-8.10\bin\gradle.bat",
        "D:\mibu-build-tools\gradle-8.10.2\bin\gradle.bat",
        (Join-Path $Root ".build-tools\gradle\gradle-8.10\bin\gradle.bat"),
        (Join-Path $Root "gradlew.bat")
    )) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Resolve-AndroidSdk {
    foreach ($candidate in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, "D:\mibu-build-tools\android-sdk", (Join-Path $Root ".build-tools\android-sdk"))) {
        if ($candidate -and (Test-Path $candidate)) { return (Resolve-Path $candidate).Path }
    }
    return $null
}

function Assert-NonEmptyFile([string]$Path, [string]$Description) {
    if (-not (Test-Path $Path) -or (Get-Item $Path).Length -le 0) {
        throw "$Description missing or empty: $Path"
    }
}

python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed with exit code $LASTEXITCODE" }
python -m pip install -r (Join-Path $HelperDir "requirements.txt") pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed with exit code $LASTEXITCODE" }

$AndroidSdk = Resolve-AndroidSdk
if ($UseExistingApk) {
    Assert-NonEmptyFile $ResolvedApk "Explicit prebuilt Android APK"
} else {
    $GradlePath = Resolve-Gradle
    if (-not $GradlePath) {
        throw "A source-fresh release requires Gradle. Expected gradle in PATH, D:\mibu-build-tools\gradle\bin\gradle.bat, D:\mibu-build-tools\gradle-8.10.2\bin\gradle.bat, or gradlew.bat in the repo. Use -UseExistingApk only for an APK already produced by the current CI commit."
    }
    if (-not $AndroidSdk) {
        throw "A source-fresh release requires Android SDK. Set ANDROID_SDK_ROOT/ANDROID_HOME or install it at D:\mibu-build-tools\android-sdk."
    }
    $LocalProperties = Join-Path $Root "local.properties"
    $EscapedSdk = $AndroidSdk.Replace('\', '\\')
    Set-Content -Path $LocalProperties -Value "sdk.dir=$EscapedSdk" -Encoding ASCII
    Push-Location $Root
    try {
        & $GradlePath :android:app:clean :android:app:lintDebug :android:app:testDebugUnitTest :android:app:assembleDebug --stacktrace
        if ($LASTEXITCODE -ne 0) { throw "Android clean/lint/test/build failed with exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    Assert-NonEmptyFile $ResolvedApk "Android APK built from current source"
}

if (-not $AndroidSdk) { $AndroidSdk = Resolve-AndroidSdk }
if (-not $AndroidSdk) {
    throw "Android SDK/platform-tools are required for a self-contained MIBU release. Set ANDROID_SDK_ROOT/ANDROID_HOME or install at D:\mibu-build-tools\android-sdk."
}
$PlatformTools = Join-Path $AndroidSdk "platform-tools"
foreach ($requiredTool in $RequiredPlatformTools) {
    Assert-NonEmptyFile (Join-Path $PlatformTools $requiredTool) "Required platform-tool"
}

Write-Host "Running source review and validating deterministic branded UI assets..." -ForegroundColor Cyan
python (Join-Path $Root "tools\extract_live_ui_assets.py")
if ($LASTEXITCODE -ne 0) { throw "Live MIBU asset extraction failed with exit code $LASTEXITCODE" }
python (Join-Path $Root "tools\review_contracts.py")
if ($LASTEXITCODE -ne 0) { throw "THETECHGUY source-contract review failed with exit code $LASTEXITCODE" }
python (Join-Path $Root "tools\review_proof_v3.py")
if ($LASTEXITCODE -ne 0) { throw "MIBU proof-v3 review failed with exit code $LASTEXITCODE" }
python (Join-Path $Root "tools\validate_android_ui_baseline.py")
if ($LASTEXITCODE -ne 0) { throw "Android expected-UI baseline validation failed with exit code $LASTEXITCODE" }
$RequiredUi = @(
    (Join-Path $Root "resources\logo.png"),
    (Join-Path $Root "resources\live_ui\mibu_logo.png"),
    (Join-Path $Root "resources\live_ui\mibu_hood.png"),
    (Join-Path $Root "resources\live_ui\mibu_app_icon.ico"),
    (Join-Path $Root "resources\live_ui\firefox.png"),
    (Join-Path $Root "resources\live_ui\chrome.png"),
    (Join-Path $Root "resources\guide\index.html"),
    (Join-Path $Root "resources\expected ui\android\approved_android_ui_baseline_sheet.svg"),
    (Join-Path $Root "resources\expected ui\android\README.md")
)
foreach ($asset in $RequiredUi) {
    Assert-NonEmptyFile $asset "Required branded UI asset"
}
$IconPath = Join-Path $Root "resources\live_ui\mibu_app_icon.ico"
$VersionPath = Join-Path $HelperDir "version_info.txt"
Assert-NonEmptyFile $VersionPath "Windows version resource"
Write-Host "Live PC UI, Android baseline, offline guide and approved application icon verified." -ForegroundColor Green

$env:QT_QPA_PLATFORM = "offscreen"
Push-Location $HelperDir
try {
    python -m unittest discover -v
    if ($LASTEXITCODE -ne 0) { throw "PC helper unit tests failed with exit code $LASTEXITCODE" }
    python -c "import mibu_actions, mibu_pc_helper_v3; assert mibu_pc_helper_v3.Window; assert mibu_actions.EXPECTED_APP_VERSION == '0.3.0-dev'; print('MIBU v3 import/version/proof-gate smoke check passed')"
    if ($LASTEXITCODE -ne 0) { throw "MIBU v3 source smoke check failed" }
} finally {
    Pop-Location
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
}

Remove-SafeDir $DistDir
Remove-SafeDir $BuildDir
Remove-SafeDir $BundleDir
New-Item -ItemType Directory -Path $BundleDir | Out-Null

Push-Location $HelperDir
try {
    python -m PyInstaller --clean --noconfirm --windowed --name "MIBU-PC-Helper" --icon $IconPath --version-file $VersionPath --hidden-import PySide6.QtMultimedia "mibu_pc_helper_v3.py"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

$BuiltHelper = Join-Path $HelperDir "dist\MIBU-PC-Helper"
if (-not (Test-Path $BuiltHelper)) { throw "PyInstaller output folder missing: $BuiltHelper" }
Copy-Item $BuiltHelper $BundleDir -Recurse -Force
$BundleApp = Join-Path $BundleDir "MIBU-PC-Helper"
$BundleDist = Join-Path $BundleApp "dist"
$BundlePlatformTools = Join-Path $BundleApp "platform-tools"
New-Item -ItemType Directory -Path $BundleDist -Force | Out-Null
New-Item -ItemType Directory -Path $BundlePlatformTools -Force | Out-Null
Copy-Item $ResolvedApk (Join-Path $BundleDist "MIBU.apk") -Force
foreach ($requiredTool in $RequiredPlatformTools) {
    Copy-Item (Join-Path $PlatformTools $requiredTool) (Join-Path $BundlePlatformTools $requiredTool) -Force
}
Write-Host "Bundled APK and Android platform-tools." -ForegroundColor Green

$ResourceRoot = Join-Path $Root "resources"
if (-not (Test-Path $ResourceRoot)) { throw "resources folder not found. Hotspot UI cannot be bundled." }
$BundleResources = Join-Path $BundleApp "resources"
Copy-Item $ResourceRoot $BundleResources -Recurse -Force

$BundledRequiredUi = @()
foreach ($asset in $RequiredUi) {
    $relative = $asset.Substring($ResourceRoot.Length).TrimStart('\')
    $bundled = Join-Path $BundleResources $relative
    Assert-NonEmptyFile $bundled "Required branded asset in release bundle"
    $BundledRequiredUi += $bundled
}

$FinalRequired = @(
    (Join-Path $BundleApp "MIBU-PC-Helper.exe"),
    (Join-Path $BundleDist "MIBU.apk")
)
foreach ($requiredTool in $RequiredPlatformTools) {
    $FinalRequired += (Join-Path $BundlePlatformTools $requiredTool)
}
foreach ($path in $FinalRequired) {
    Assert-NonEmptyFile $path "Final release file"
}

$AudioRoots = @(
    (Join-Path $Root "resources\expected ui"),
    (Join-Path $Root "resources\expected ui\android"),
    (Join-Path $Root "resources")
)
$BundledAudio = @()
foreach ($name in @("TTG_v4_clean_connected_success.wav", "TTG_v4_clean_speaker_turn_on.wav")) {
    $found = $false
    foreach ($dir in $AudioRoots) {
        $candidate = Join-Path $dir $name
        if (Test-Path $candidate) {
            $destination = Join-Path $BundleDist $name
            Copy-Item $candidate $destination -Force
            $BundledAudio += $destination
            $found = $true
            break
        }
    }
    if (-not $found) { Write-Warning "Optional audio not found: $name" }
}

$ChecksumTargets = @($FinalRequired + $BundledRequiredUi + $BundledAudio) |
    Sort-Object -Unique
$ChecksumLines = foreach ($item in $ChecksumTargets) {
    Assert-NonEmptyFile $item "Checksummed release file"
    $hash = (Get-FileHash -Algorithm SHA256 $item).Hash.ToLowerInvariant()
    $relative = $item.Substring($BundleApp.Length).TrimStart('\').Replace('\', '/')
    "$hash  $relative"
}
$ChecksumPath = Join-Path $BundleApp "SHA256SUMS.txt"
Set-Content -Path $ChecksumPath -Value $ChecksumLines -Encoding ASCII
Assert-NonEmptyFile $ChecksumPath "Release checksum manifest"
if ((Get-Content $ChecksumPath).Count -ne $ChecksumTargets.Count) {
    throw "Release checksum manifest count does not match the protected release-file count."
}

# Keep PyInstaller's normal dist path runnable too. This prevents a correct-icon
# executable there from failing because only the release copy received assets.
foreach ($folder in @("dist", "platform-tools", "resources")) {
    Copy-Item (Join-Path $BundleApp $folder) (Join-Path $BuiltHelper $folder) -Recurse -Force
}
Copy-Item $ChecksumPath (Join-Path $BuiltHelper "SHA256SUMS.txt") -Force
Assert-NonEmptyFile (Join-Path $BuiltHelper "dist\MIBU.apk") "PyInstaller runtime APK"
Assert-NonEmptyFile (Join-Path $BuiltHelper "resources\live_ui\mibu_logo.png") "PyInstaller runtime branding"

$IconRefresh = "$env:SystemRoot\System32\ie4uinit.exe"
foreach ($argument in @("-ClearIconCache", "-show")) {
    Start-Process -FilePath $IconRefresh -ArgumentList $argument -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
}
try {
    $shell = New-Object -ComObject Shell.Application
    @($shell.Windows()) | ForEach-Object { $_.Refresh() }
} catch {
    Write-Verbose "Explorer icon refresh was unavailable: $($_.Exception.Message)"
}
Write-Host "Both runnable EXE folders, APK, platform-tools, live UI, approved icon and SHA-256 manifest verified." -ForegroundColor Green
Write-Host "Release folder: $BundleDir" -ForegroundColor Green
