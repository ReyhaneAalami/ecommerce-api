param(
    [string]$HostUrl = "http://127.0.0.1:8000",
    [int]$Users = 10,
    [double]$SpawnRate = 2,
    [string]$RunTime = "2m"
)

$ErrorActionPreference = "Stop"
$Python = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found at $Python"
}

& $Python -m locust -f .\locustfile.py `
    --host $HostUrl `
    --users $Users `
    --spawn-rate $SpawnRate `
    --run-time $RunTime `
    --headless `
    --csv ".\reports\locust"
