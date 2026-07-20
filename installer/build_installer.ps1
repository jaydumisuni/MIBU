param([string]$IsccPath = "")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Release = Join-Path $Root "pc-helper\release\MIBU-PC-Helper"
$Script = Join-Path $PSScriptRoot "MIBU-PC-Helper.iss"

if (-not (Test-Path (Join-Path $Release "MIBU-PC-Helper.exe"))) {
    throw "Build the complete PC helper release before compiling the installer."
}

if (-not $IsccPath) {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
    )
    $IsccPath = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $IsccPath) { throw "Inno Setup 6 compiler was not found." }

& $IsccPath $Script
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

$Installer = Join-Path $PSScriptRoot "output\MIBU-PC-Helper-Setup-0.3.0.exe"
if (-not (Test-Path $Installer) -or (Get-Item $Installer).Length -le 0) {
    throw "Installer output is missing or empty: $Installer"
}
$Hash = (Get-FileHash -Algorithm SHA256 $Installer).Hash.ToLowerInvariant()
Set-Content -Path (Join-Path $PSScriptRoot "output\SHA256SUMS.txt") -Value "$Hash  MIBU-PC-Helper-Setup-0.3.0.exe" -Encoding ASCII
Write-Host "Installer: $Installer" -ForegroundColor Green
