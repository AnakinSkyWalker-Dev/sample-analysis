$ErrorActionPreference = "Stop"

$mainDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDirectory = Split-Path -Parent $mainDirectory
$python = Join-Path $projectDirectory ".venv\Scripts\python.exe"
$entryPoint = Join-Path $mainDirectory "main.py"
$workDirectory = Join-Path $mainDirectory ".cache\pyinstaller"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found: $python"
}

& $python -m pip install -r (Join-Path $mainDirectory "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install build/runtime dependencies."
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --collect-all customtkinter `
    --collect-all tkinter `
    --name TCC `
    --distpath $projectDirectory `
    --workpath $workDirectory `
    --specpath $mainDirectory `
    $entryPoint
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Output "Executable created: $(Join-Path $projectDirectory 'TCC.exe')"
