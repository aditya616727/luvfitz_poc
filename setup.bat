@echo off
REM ─────────────────────────────────────────────────────
REM  Mini Outfit Builder – Quick Start (Windows CMD)
REM ─────────────────────────────────────────────────────
REM  Usage:
REM    setup.bat              Full setup: build + seed + open
REM    setup.bat --build      Rebuild containers only
REM    setup.bat --seed       Re-seed database only
REM    setup.bat --stop       Stop all containers
REM    setup.bat --reset      Nuke everything and start fresh
REM ─────────────────────────────────────────────────────
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ======================================
echo   Mini Outfit Builder - Setup
echo ======================================
echo.

REM ── Check Docker ──
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    echo         Please install and start Docker Desktop:
    echo         https://docs.docker.com/get-docker/
    exit /b 1
)
echo [OK] Docker is running

REM ── Check Docker Compose ──
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose not found.
    echo         Please install Docker Desktop (includes Compose).
    exit /b 1
)
echo [OK] Docker Compose available

REM ── Create .env if missing ──
if not exist .env (
    echo [INFO] Creating .env with defaults...
    (
        echo # --- Environment ---
        echo POSTGRES_USER=outfit_user
        echo POSTGRES_PASSWORD=outfit_secret_pw
        echo POSTGRES_DB=outfit_builder
        echo POSTGRES_HOST=postgres
        echo POSTGRES_PORT=5432
        echo DATABASE_URL=postgresql://outfit_user:outfit_secret_pw@postgres:5432/outfit_builder
        echo.
        echo REDIS_URL=redis://redis:6379/0
        echo.
        echo # --- Celery ---
        echo CELERY_BROKER_URL=redis://redis:6379/1
        echo CELERY_RESULT_BACKEND=redis://redis:6379/2
        echo.
        echo # --- App ---
        echo APP_ENV=production
        echo LOG_LEVEL=INFO
        echo SECRET_KEY=change-me-in-production
        echo.
        echo # --- Scraping ---
        echo SCRAPE_CONCURRENCY=3
        echo SCRAPE_DELAY_SECONDS=2
        echo USER_AGENT=Mozilla/5.0 ^(Windows NT 10.0; Win64; x64^) AppleWebKit/537.36
        echo.
        echo # --- Server / Nginx ---
        echo NGINX_PORT=80
        echo.
        echo # --- Frontend ---
        echo NEXT_PUBLIC_API_URL=
    ) > .env
    echo [OK] .env created
) else (
    echo [OK] .env already exists
)

REM ── Parse argument ──
if "%~1"=="--build"  goto :do_build
if "%~1"=="--seed"   goto :do_seed
if "%~1"=="--stop"   goto :do_stop
if "%~1"=="--reset"  goto :do_reset
if "%~1"=="--status" goto :do_status
if "%~1"==""         goto :do_full
goto :usage

REM ── Commands ──

:do_full
call :do_build_impl
call :do_wait_impl
call :do_seed_impl
call :do_status_impl
call :print_urls
goto :eof

:do_build
call :do_build_impl
call :do_wait_impl
call :do_status_impl
goto :eof

:do_seed
call :do_seed_impl
goto :eof

:do_stop
echo.
echo -- Stopping all containers --
docker compose down
echo [OK] All containers stopped
goto :eof

:do_reset
echo.
echo -- Resetting everything --
docker compose down -v 2>nul
echo [OK] Containers and volumes removed
call :do_build_impl
call :do_wait_impl
call :do_seed_impl
call :do_status_impl
call :print_urls
goto :eof

:do_status
call :do_status_impl
goto :eof

REM ── Implementations ──

:do_build_impl
echo.
echo -- Building and starting containers --
docker compose up --build -d
echo [OK] All containers started
goto :eof

:do_wait_impl
echo.
echo -- Waiting for backend to be ready --
set /a attempts=0
set /a max_attempts=30
:wait_loop
if !attempts! geq !max_attempts! (
    echo.
    echo [WARN] Backend did not respond within 60s, may still be starting...
    goto :eof
)
curl -sf http://localhost:8000/health >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [OK] Backend API is healthy
    goto :eof
)
set /a attempts+=1
<nul set /p "=."
timeout /t 2 /nobreak >nul
goto :wait_loop

:do_seed_impl
echo.
echo -- Seeding database --
docker compose exec -T backend python -m app.scripts.seed 2>&1 | findstr /i "Seeded Generated stats"
echo [OK] Database seeded with products and outfits
goto :eof

:do_status_impl
echo.
echo -- Service Status --
docker compose ps
goto :eof

:print_urls
echo.
echo ======================================
echo   Setup Complete!
echo ======================================
echo.
echo   Frontend:   http://localhost
echo   API Docs:   http://localhost/docs
echo   Health:     http://localhost/health
echo   Backend:    http://localhost:8000/docs
echo.
echo   Commands:
echo     docker compose logs -f        Follow logs
echo     docker compose ps             Service status
echo     setup.bat --seed              Re-seed database
echo     setup.bat --stop              Stop everything
echo     setup.bat --reset             Nuke and rebuild
echo.
goto :eof

:usage
echo.
echo Usage: setup.bat [--build^|--seed^|--stop^|--reset^|--status]
echo.
echo   (no args)   Full setup: build + seed + show URLs
echo   --build     Rebuild containers only
echo   --seed      Re-seed database only
echo   --stop      Stop all containers
echo   --reset     Nuke volumes and start completely fresh
echo   --status    Show container status
exit /b 1
