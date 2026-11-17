param([switch]$Offline, [int]$Port = 8010)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$demoPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) {
    throw 'Create the environment first: py -m venv .venv; then .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
}
# Override only this launch; do not modify credentials or the local .env file.
$demoNames = @('AGENT_MODE','DEMO_MODE','STORAGE','MONGODB_DB','SQLITE_PATH')
$demoPrevious = @{}
foreach ($demoName in $demoNames) { $demoPrevious[$demoName] = [Environment]::GetEnvironmentVariable($demoName, 'Process') }
try {
    $env:AGENT_MODE = 'scripted'
    $env:DEMO_MODE = 'true'
    $demoRun = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    if ($Offline) {
        $env:STORAGE = 'sqlite'
        $env:SQLITE_PATH = Join-Path $PSScriptRoot "demo-$demoRun.sqlite"
        Write-Host 'OFFLINE rehearsal: local SQLite storage, no Atlas connection.'
    } else {
        $env:STORAGE = 'mongo'
        $env:MONGODB_DB = "splitsmart_demo_$demoRun"
        Write-Host "Atlas demo database: $env:MONGODB_DB"
    }
    Write-Host "Open http://127.0.0.1:$Port and follow DEMO-SCRIPT.md. Ctrl+C stops the server."
    Write-Host 'Each launch uses fresh demo data without deleting previous data. Responses are scripted.'
    & $demoPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally {
    foreach ($demoName in $demoNames) { [Environment]::SetEnvironmentVariable($demoName, $demoPrevious[$demoName], 'Process') }
}
