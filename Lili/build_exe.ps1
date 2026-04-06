Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specFile = Join-Path $projectRoot "Lili.spec"

if (-not (Test-Path $venvPython)) {
    throw "Python da virtualenv nao encontrado em $venvPython"
}

& $venvPython -c "import PyInstaller" 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller nao instalado na virtualenv. Rode: .\.venv\Scripts\python.exe -m pip install pyinstaller"
}

& $venvPython -m PyInstaller --noconfirm --clean $specFile
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao gerar o executavel."
}

Write-Host "Build concluido em: $projectRoot\dist\Lili\Lili.exe"
