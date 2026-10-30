$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputDir = Join-Path $projectRoot "milestone2\src"
Set-Location $projectRoot

python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name EncryptedMessenger_ALL_IN_ONE `
    --distpath $outputDir `
    setup_infra.py

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Application `
    --distpath $outputDir `
    application.py

Write-Host "Built: $outputDir\EncryptedMessenger_ALL_IN_ONE.exe"
Write-Host "Built: $outputDir\Application.exe"
