# PowerShell Makefile equivalent for Windows
# Usage: .\make.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$APP_DIR = "app"
$TEST_DIR = "tests"

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  help        " -NoNewline -ForegroundColor Green
    Write-Host "Show this help message"
    Write-Host "  install     " -NoNewline -ForegroundColor Green
    Write-Host "Install Python dependencies"
    Write-Host "  format      " -NoNewline -ForegroundColor Green
    Write-Host "Format code with black"
    Write-Host "  lint        " -NoNewline -ForegroundColor Green
    Write-Host "Run pylint checks"
    Write-Host "  test        " -NoNewline -ForegroundColor Green
    Write-Host "Run tests with coverage"
    Write-Host "  check       " -NoNewline -ForegroundColor Green
    Write-Host "Run format, lint, and tests"
    Write-Host "  run-local   " -NoNewline -ForegroundColor Green
    Write-Host "Run FastAPI app locally"
    Write-Host "  clean       " -NoNewline -ForegroundColor Green
    Write-Host "Remove Python cache files"
    Write-Host "  all         " -NoNewline -ForegroundColor Green
    Write-Host "Install dependencies and run all checks"
}

function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    uv sync
}

function Format-Code {
    Write-Host "Formatting code..." -ForegroundColor Yellow
    black $APP_DIR $TEST_DIR
}

function Invoke-Linter {
    Write-Host "Running pylint..." -ForegroundColor Yellow
    pylint --disable=R,C $APP_DIR $TEST_DIR
}

function Test-Code {
    Write-Host "Running tests..." -ForegroundColor Yellow
    python -m pytest --verbose --cov=app tests/
}

function Check-All {
    Format-Code
    Invoke-Linter
    Test-Code
}

function Start-Local {
    Write-Host "Starting FastAPI locally..." -ForegroundColor Yellow
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
}

function Clear-Cache {
    Write-Host "Cleaning Python cache files..." -ForegroundColor Yellow
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Recurse -Directory -Filter ".coverage" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Cleanup complete!" -ForegroundColor Green
}

function Invoke-All {
    Install-Dependencies
    Check-All
}

# Execute command
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "format" { Format-Code }
    "lint" { Invoke-Linter }
    "test" { Test-Code }
    "check" { Check-All }
    "run-local" { Start-Local }
    "clean" { Clear-Cache }
    "all" { Invoke-All }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
