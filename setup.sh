#!/usr/bin/env bash
# ─────────────────────────────────────────────────────
# Mini Outfit Builder – Quick Start (macOS / Linux)
# ─────────────────────────────────────────────────────
# Usage:
#   chmod +x setup.sh
#   ./setup.sh              # full setup: build + seed + open
#   ./setup.sh --build      # rebuild containers only
#   ./setup.sh --seed       # re-seed database only
#   ./setup.sh --stop       # stop all containers
#   ./setup.sh --reset      # nuke everything and start fresh
# ─────────────────────────────────────────────────────
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# ── Helpers ──────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║     👗 Mini Outfit Builder – Setup       ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

log_info()    { echo -e "  ${CYAN}ℹ${NC}  $1"; }
log_success() { echo -e "  ${GREEN}✅${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
log_error()   { echo -e "  ${RED}❌${NC} $1"; }
log_step()    { echo -e "\n${BOLD}── $1 ──${NC}"; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop:"
        echo "       https://docs.docker.com/get-docker/"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    log_success "Docker is running"
}

check_compose() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose not found. Please install Docker Desktop (includes Compose)."
        exit 1
    fi
    log_success "Docker Compose available (${COMPOSE_CMD})"
}

wait_for_healthy() {
    local url="$1"
    local label="$2"
    local max_wait=60
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$label is healthy"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
        printf "."
    done

    echo ""
    log_warn "$label did not respond within ${max_wait}s (may still be starting)"
    return 1
}

ensure_env() {
    if [ ! -f .env ]; then
        log_info "Creating .env with default settings..."
        cat > .env << 'ENVEOF'
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
USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36

# ─── Server / Nginx ───
NGINX_PORT=80

# ─── Frontend ───
NEXT_PUBLIC_API_URL=
ENVEOF
        log_success ".env created"
    else
        log_success ".env already exists"
    fi
}

# ── Commands ─────────────────────────────────────────

do_build() {
    log_step "Building & starting containers"
    $COMPOSE_CMD up --build -d
    log_success "All containers started"
}

do_wait() {
    log_step "Waiting for services"
    echo -n "  "
    wait_for_healthy "http://localhost:8000/health" "Backend API"
}

do_seed() {
    log_step "Seeding database"
    $COMPOSE_CMD exec -T backend python -m app.scripts.seed 2>&1 | tail -5
    log_success "Database seeded with products & outfits"
}

do_status() {
    log_step "Service status"
    $COMPOSE_CMD ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE_CMD ps
}

do_stop() {
    log_step "Stopping all containers"
    $COMPOSE_CMD down
    log_success "All containers stopped"
}

do_reset() {
    log_step "Resetting everything (containers + volumes)"
    $COMPOSE_CMD down -v 2>/dev/null || true
    log_success "Containers and volumes removed"
}

print_urls() {
    local port
    port=$(grep -E "^NGINX_PORT=" .env 2>/dev/null | cut -d= -f2 || echo "80")
    port="${port:-80}"

    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║           🎉 Setup Complete!             ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Frontend:${NC}   http://localhost:${port}"
    echo -e "  ${BOLD}API Docs:${NC}   http://localhost:${port}/docs"
    echo -e "  ${BOLD}Health:${NC}     http://localhost:${port}/health"
    echo -e "  ${BOLD}Backend:${NC}    http://localhost:8000/docs"
    echo ""
    echo -e "  ${CYAN}Useful commands:${NC}"
    echo "    $COMPOSE_CMD logs -f          # follow logs"
    echo "    $COMPOSE_CMD ps               # service status"
    echo "    ./setup.sh --seed             # re-seed database"
    echo "    ./setup.sh --stop             # stop everything"
    echo "    ./setup.sh --reset            # nuke & rebuild"
    echo ""
}

# ── Main ─────────────────────────────────────────────

print_banner
check_docker
check_compose
ensure_env

case "${1:-}" in
    --build)
        do_build
        do_wait
        do_status
        ;;
    --seed)
        do_seed
        ;;
    --stop)
        do_stop
        ;;
    --reset)
        do_reset
        do_build
        do_wait
        do_seed
        do_status
        print_urls
        ;;
    --status)
        do_status
        ;;
    ""|--start)
        do_build
        do_wait
        do_seed
        do_status
        print_urls
        ;;
    *)
        echo "Usage: ./setup.sh [--build|--seed|--stop|--reset|--status]"
        echo ""
        echo "  (no args)   Full setup: build + seed + show URLs"
        echo "  --build     Rebuild containers only"
        echo "  --seed      Re-seed database only"
        echo "  --stop      Stop all containers"
        echo "  --reset     Nuke volumes and start completely fresh"
        echo "  --status    Show container status"
        exit 1
        ;;
esac
