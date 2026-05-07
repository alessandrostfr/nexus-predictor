# Runs the V2 PostgreSQL migrations.
# Run from the project root with PowerShell.

Set-Location "$PSScriptRoot\.."

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

docker compose up -d postgres

Set-Location "$PSScriptRoot\..\backend"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

if (Test-Path ".venv\Scripts\Activate.ps1") {
  . .\.venv\Scripts\Activate.ps1
}

alembic -c alembic.ini upgrade head
python scripts/check_v2_foundations.py
