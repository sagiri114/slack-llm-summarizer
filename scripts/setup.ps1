$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example. Please edit it before running the bot."
} else {
    Write-Host ".env already exists."
}

pip install -e ".[dev]"
Write-Host "Done. Next: edit .env, then run scripts/dev.ps1"
