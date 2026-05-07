# Runs the main release checks for Nexus Predictor.
# Run from the project root with PowerShell.

Set-Location "$PSScriptRoot\.."

docker compose up -d postgres

Set-Location "$PSScriptRoot\..\backend"
. .\.venv\Scripts\Activate.ps1
python scripts/check_environment.py
alembic -c alembic.ini upgrade head
python scripts/check_v2_foundations.py
python scripts/validate_dataset.py
python scripts/generate_predictions.py --year 2026
pytest

Set-Location "$PSScriptRoot\..\frontend"
npm install
npm run build

Write-Host "Release checks completed successfully."
