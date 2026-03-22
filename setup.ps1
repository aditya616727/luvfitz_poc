# ─────────────────────────────────────────────────────
#  Mini Outfit Builder – Quick Start (Windows PowerShell)
# ─────────────────────────────────────────────────────
#  Usage:
#    .\setup.ps1              Full setup: build + seed + open
#    .\setup.ps1 -Action build    Rebuild containers only
#    .\setup.ps1 -Action seed     Re-seed database only
#    .\setup.ps1 -Action stop     Stop all containers
#    .\setup.ps1 -Action reset    Nuke everything and start fresh
#    .\setup.ps1 -Action status   Show container status
# ─────────────────────────────────────────────────────
param(
    [ValidateSet("start", "build", "seed", "stop", "reset", "status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# ── Helpers ──────────────────────────────────────────

function Write-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║     👗 Mini Outfit Builder – Setup       ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($msg)    { Write-Host "`n── $msg ──" -ForegroundColor White }
function Write-OK($msg)      { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Err($msg)     { Write-Host "  ❌ $msg" -ForegroundColor Red }
function Write-Info($msg)    { Write-Host "  ℹ  $msg" -ForegroundColor Cyan }

function Test-Docker {
    try {
        $null = docker info 2>&1
        if ($LASTEXITCODE -ne 0) { throw "not running" }
        Write-OK "Docker is running"
    }
    catch {
        Write-Err "Docker is not running. Please install & start Docker Desktop:"
        Write-Host "       https://docs.docker.com/get-docker/"
        exit 1
    }
}

function Test-Compose {
    try {
        $null = docker compose version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "missing" }
        Write-OK "Docker Compose available"
    }
    catch {
        Write-Err "Docker Compose not found. Please install Docker Desktop."
        exit 1
    }
}

function Ensure-Env {
    if (-not (Test-Path ".env")) {
        Write-Info "Creating .env with default settings..."
        @"
# ─── Environment ───
POSTGRES_USER=outfit_user
POSTGRES_PASSWORD=outfit_secret_pw
POSTGRES_DB=outfit_builder
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://outfit_user:outfit_secret_pw@postgres:5432/outfit_builder

REDIS_URL=redis://redis:6379/0

# ─── Celery ───
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# ─── App ───
APP_ENV=production
LOG_LEVEL=INFO
SECRET_KEY=change-me-in-production

# ─── Scraping ───
SCRAPE_CONCURRENCY=3
SCRAPE_DELAY_SECONDS=2
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# ─── Server / Nginx ───
NGINX_PORT=80

# ─── Frontend ───
NEXT_PUBLIC_API_URL=
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-OK ".env created"
    }
    else {
        Write-OK ".env already exists"
    }
}

function Invoke-Build {
    Write-Step "Fixing line endings for Docker (Windows CRLF → LF)"
    # Git may check out files with CRLF on Windows.
    # Re-normalise so Dockerfiles/scripts inside containers have LF.
    try {
        git ls-files -z | ForEach-Object { $_ } | Out-Null
        git add --renormalize . 2>$null
        git checkout -- . 2>$null
    } catch { }
    Write-OK "Line endings normalised"

    Write-Step "Building & starting containers"
    docker compose up --build -d
    if ($LASTEXITCODE -ne 0) { Write-Err "Build failed"; exit 1 }
    Write-OK "All containers started"
}

function Wait-ForHealthy {
    Write-Step "Waiting for services"
    $maxWait = 60
    $waited = 0

    while ($waited -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-OK "Backend API is healthy"
                return
            }
        }
        catch { }

        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
        $waited += 2
    }

    Write-Host ""
    Write-Warn "Backend did not respond within ${maxWait}s (may still be starting)"
}

function Invoke-Seed {
    Write-Step "Seeding database"
    docker compose exec -T backend python -m app.scripts.seed 2>&1 | Select-String -Pattern "Seeded|Generated|stats"
    Write-OK "Database seeded with products & outfits"
}

function Show-Status {
    Write-Step "Service status"
    docker compose ps
}

function Invoke-Stop {
    Write-Step "Stopping all containers"
    docker compose down
    Write-OK "All containers stopped"
}

function Invoke-Reset {
    Write-Step "Resetting everything (containers + volumes)"
    docker compose down -v 2>$null
    Write-OK "Containers and volumes removed"
}

function Show-Urls {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║           🎉 Setup Complete!             ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend:   " -NoNewline; Write-Host "http://localhost" -ForegroundColor Cyan
    Write-Host "  API Docs:   " -NoNewline; Write-Host "http://localhost/docs" -ForegroundColor Cyan
    Write-Host "  Health:     " -NoNewline; Write-Host "http://localhost/health" -ForegroundColor Cyan
    Write-Host "  Backend:    " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Useful commands:" -ForegroundColor White
    Write-Host "    docker compose logs -f          # follow logs"
    Write-Host "    docker compose ps               # service status"
    Write-Host "    .\setup.ps1 -Action seed        # re-seed database"
    Write-Host "    .\setup.ps1 -Action stop        # stop everything"
    Write-Host "    .\setup.ps1 -Action reset       # nuke & rebuild"
    Write-Host ""
}

# ── Main ─────────────────────────────────────────────

Write-Banner
Test-Docker
Test-Compose
Ensure-Env

switch ($Action) {
    "start" {
        Invoke-Build
        Wait-ForHealthy
        Invoke-Seed
        Show-Status
        Show-Urls
    }
    "build" {
        Invoke-Build
        Wait-ForHealthy
        Show-Status
    }
    "seed" {
        Invoke-Seed
    }
    "stop" {
        Invoke-Stop
    }
    "reset" {
        Invoke-Reset
        Invoke-Build
        Wait-ForHealthy
        Invoke-Seed
        Show-Status
        Show-Urls
    }
    "status" {
        Show-Status
    }
}
