# run.ps1 - helper commands for PowerShell
# Usage:
#   .\run.ps1 install
#   .\run.ps1 run
#   .\run.ps1 test
#   .\run.ps1 clean

param (
    [Parameter(Position=0)]
    [ValidateSet("install", "run", "test", "clean")]
    [string]$task = "run"
)

switch ($task) {
    "install" {
        pip install -r requirements.txt
        break
    }
    "run" {
        uvicorn app.main:app --reload --port 8001
        break
    }
    "test" {
        pytest -q
        break
    }
    "clean" {
        Remove-Item -Recurse -Force __pycache__, .pytest_cache -ErrorAction SilentlyContinue
        break
    }
}