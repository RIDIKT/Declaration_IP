$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Find-Python {
    $candidates = @()
    $candidates += Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $candidates += Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    foreach ($version in @('313', '312', '311')) {
        $candidates += "$env:LOCALAPPDATA\Programs\Python\Python$version\python.exe"
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate) -and $candidate -notlike '*\WindowsApps\*') {
            & $candidate -c "import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
}

try {
    $python = Find-Python
    if (-not $python) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
            throw 'Install Python 3.11-3.13 from python.org, then run this file again.'
        }
        Write-Host 'Installing Python 3.13. Please wait...'
        & winget.exe install --id Python.Python.3.13 --exact --source winget --scope user --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw 'Python installation failed. Install Python 3.13 from python.org and retry.' }
        $python = Find-Python
        if (-not $python) { throw 'Python was not found. Restart this launcher after installing Python 3.13.' }
    }
    $venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host 'Preparing application environment...'
        & $python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
    }
    $stamp = Join-Path $PSScriptRoot '.venv\requirements.sha256'
    $hash = (Get-FileHash -LiteralPath requirements.txt -Algorithm SHA256).Hash
    if (-not (Test-Path -LiteralPath $stamp) -or (Get-Content -LiteralPath $stamp -Raw).Trim() -ne $hash) {
        Write-Host 'Installing dependencies (Internet required on first launch)...'
        & $venvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your Internet connection and retry.' }
        Set-Content -LiteralPath $stamp -Value $hash
    }
    Write-Host 'Starting application. Keep this window open; press Ctrl+C to stop.'
    & $venvPython app.py
    if ($LASTEXITCODE -ne 0) { throw 'Application stopped with an error. See the message above.' }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
