# Run only on a disposable native Windows x64 CI runner with an interactive desktop.
param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [string]$Python = 'python',
    [string]$Repo = (Resolve-Path "$PSScriptRoot\..\.."),
    [switch]$AllowDisposableRunner
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Installer qualification must run with a non-elevated token' }
if (-not $AllowDisposableRunner) { throw 'Explicit -AllowDisposableRunner required (installs/removes Filecraft)' }
$Installer = (Resolve-Path $Installer).Path
$App = Join-Path $env:LOCALAPPDATA 'Programs\Filecraft'
$Registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Filecraft.Desktop_is1'
if ((Test-Path $App) -or (Test-Path $Registry)) { throw 'Refusing to overwrite an existing Filecraft installation' }
$Metadata = Get-Content "$Installer.metadata.json" -Raw | ConvertFrom-Json
if ((Get-FileHash $Installer -Algorithm SHA256).Hash.ToLower() -ne $Metadata.sha256) { throw 'Installer digest mismatch' }
$SentinelDir = Join-Path $env:LOCALAPPDATA ('Filecraft-packaging-test-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $SentinelDir | Out-Null
$Sentinel = Join-Path $SentinelDir 'user-data.txt'
Set-Content $Sentinel 'synthetic user data; must survive uninstall'
function Run-Setup {
    $p = Start-Process -FilePath $Installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-' -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Installer exit $($p.ExitCode)" }
    if (-not (Test-Path $Registry)) { throw 'Missing per-user uninstall registration' }
    $link = Join-Path ([Environment]::GetFolderPath('Programs')) 'Filecraft.lnk'
    if (-not (Test-Path $link)) { throw 'Missing Start menu shortcut' }
    foreach ($entry in $Metadata.bundle_files.PSObject.Properties) {
        $file = Join-Path $App $entry.Name
        if ((Get-FileHash $file -Algorithm SHA256).Hash.ToLower() -ne $entry.Value) { throw "Installed byte mismatch: $($entry.Name)" }
    }
    & $Python "$Repo\desktop\check_frozen.py" "$App\Filecraft-Desktop.exe"
    if ($LASTEXITCODE -ne 0) { throw 'Installed frozen runtime failed real conversion checks' }
}
function Check-Gui {
    $launcher = Start-Process -FilePath "$App\Filecraft.exe" -PassThru
    $gui = $null
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        $gui = Get-Process -Name 'Filecraft-Desktop' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq "$App\Filecraft-Desktop.exe" -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
        if ($gui) { break }
        if ($launcher.HasExited) { throw 'GUI launcher exited before a visible window appeared' }
        Start-Sleep -Milliseconds 250
    }
    if (-not $gui) { throw 'No MainWindowHandle; worker success is not GUI evidence' }
    if (-not $gui.CloseMainWindow()) { throw 'GUI refused normal close' }
    if (-not $gui.WaitForExit(15000)) { throw 'GUI did not quit' }
    if (-not $launcher.WaitForExit(15000) -or $launcher.ExitCode -ne 0) { throw 'GUI launcher did not exit cleanly' }
}
try {
    Run-Setup
    Check-Gui
    & $Python "$Repo\distribution\test_installed_gui.py" --executable "$App\Filecraft.exe" --evidence "$Repo\build\distribution-evidence"
    if ($LASTEXITCODE -ne 0) { throw "Installed GUI import/export failed" }
    Check-Gui # Relaunch after normal quit.
    Run-Setup # Same-version reinstall: stable identity, no duplicate install.
    Check-Gui
    $uninstall = Start-Process "$App\unins000.exe" -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait -PassThru
    if ($uninstall.ExitCode -ne 0) { throw 'Uninstaller failed' }
    if ((Test-Path "$App\Filecraft.exe") -or (Test-Path "$App\Filecraft-Desktop.exe") -or (Test-Path $Registry)) { throw 'Installed executable/registration remains' }
    if (Test-Path (Join-Path ([Environment]::GetFolderPath('Programs')) 'Filecraft.lnk')) { throw 'Shortcut remains' }
    if (-not (Test-Path $Sentinel)) { throw 'User data was removed' }
    Write-Output 'PASS native Windows install/reinstall/uninstall, runtime bytes, frozen exports, GUI window/quit/relaunch. OS-input GUI export tested.'
} finally {
    # Retain failed installation for diagnosis; remove only this test-owned sentinel.
    Remove-Item $SentinelDir -Recurse -Force
}
