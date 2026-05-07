# Starts the Nexus Predictor backend in local development mode.
# Run from the project root with PowerShell.

Set-Location "$PSScriptRoot\..\backend"

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
  Write-Host "Creating backend virtual environment..."
  py -3.11 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

python scripts/check_environment.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
