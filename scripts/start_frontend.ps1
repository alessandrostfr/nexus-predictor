# Starts the Nexus Predictor frontend in local development mode.
# Run from the project root with PowerShell.

Set-Location "$PSScriptRoot\..\frontend"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

npm install
npm run dev
