# CI-only: use the existing interactive user's limited token, never credentials.
param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
if ($env:RUNNER_OS -ne 'Windows' -or $env:GITHUB_ACTIONS -ne 'true') { throw 'Disposable GitHub Windows runner only' }
$Installer=(Resolve-Path $Installer).Path
$repo=(Resolve-Path "$PSScriptRoot\..\..").Path
$evidence=Join-Path $repo 'build\standard-user'
New-Item -ItemType Directory -Force $evidence | Out-Null
$result=Join-Path $evidence 'exit.txt'
$script=Join-Path $evidence 'run.ps1'
# Single-quote escaped paths; no user-controlled command interpolation.
$test=(Join-Path $PSScriptRoot 'test-install.ps1').Replace("'","''")
$inst=$Installer.Replace("'","''")
$res=$result.Replace("'","''")
$log=(Join-Path $evidence 'native.log').Replace("'","''")
$python=(Get-Command python).Source.Replace("'","''")
@"
`$ErrorActionPreference='Stop'
try {
    & '$test' -Installer '$inst' -Python '$python' -AllowDisposableRunner *> '$log'
    Set-Content '$res' '0'
} catch {
    `$_ | Out-String | Add-Content '$log'
    Set-Content '$res' '1'
    exit 1
}
"@ | Set-Content -Encoding utf8 $script
$name='Filecraft-StandardUser-'+[guid]::NewGuid().ToString('N')
$action=New-ScheduledTaskAction -Execute (Get-Command pwsh).Source -Argument "-NoProfile -ExecutionPolicy RemoteSigned -File `"$script`"" -WorkingDirectory $repo
$principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
try {
    Register-ScheduledTask -TaskName $name -Action $action -Principal $principal | Out-Null
    Start-ScheduledTask -TaskName $name
    $deadline=(Get-Date).AddMinutes(10)
    while (-not (Test-Path $result)) {
        if ((Get-Date) -gt $deadline) { throw 'Standard-user interactive qualification timed out' }
        Start-Sleep -Seconds 2
    }
    Get-Content (Join-Path $evidence 'native.log')
    if ((Get-Content $result).Trim() -ne '0') { throw 'Standard-user qualification failed' }
} finally {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}
