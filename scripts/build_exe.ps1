# Builds dist/VoiceBridge/VoiceBridge.exe from the committed PyInstaller spec.
# Run from the project root: powershell -File scripts/build_exe.ps1

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

.\.venv\Scripts\pip install -r requirements-dev.txt -q

.\.venv\Scripts\python -m PyInstaller --noconfirm VoiceBridge.spec

Write-Host "Built: dist\VoiceBridge\VoiceBridge.exe"
