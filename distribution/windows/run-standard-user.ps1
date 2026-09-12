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
    Start-Transcript -Path '$log' -Force | Out-Null
    & '$test' -Installer '$inst' -Python '$python' -AllowDisposableRunner
    Stop-Transcript | Out-Null
    Set-Content '$res' '0'
} catch {
    Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
    `$_ | Out-String | Add-Content '$log'
    Set-Content '$res' '1'
    exit 1
}
"@ | Set-Content -Encoding utf8 $script
$runner=Join-Path $repo 'build\restricted-run.exe'
& $runner (Get-Command pwsh).Source $script
$code=$LASTEXITCODE
if (Test-Path (Join-Path $evidence 'native.log')) { Get-Content (Join-Path $evidence 'native.log') }
if ($code -ne 0 -or -not (Test-Path $result) -or (Get-Content $result).Trim() -ne '0') { throw 'Restricted standard-user qualification failed' }
