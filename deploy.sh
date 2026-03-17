#!/bin/bash
# ─────────────────────────────────────────────
# Mini Outfit Builder – Production Deploy Script
# ─────────────────────────────────────────────
set -e

echo "🚀 Mini Outfit Builder – Production Deploy"
echo "============================================"

# Check for .env file
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your settings, then run this script again."
    exit 1
fi

# Source .env
set -a
source .env
set +a

# Detect public IP if SERVER_HOST not set
if [ -z "$SERVER_HOST" ]; then
    echo "🔍 Detecting public IP..."
    SERVER_HOST=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "localhost")
    echo "   Detected: $SERVER_HOST"
fi

echo ""
echo "📦 Building and starting all services..."
docker compose down 2>/dev/null || true
docker compose up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo ""
echo "🏥 Health check..."
if curl -sf http://localhost:${NGINX_PORT:-80}/health > /dev/null 2>&1; then
    echo "   ✅ Backend API is healthy"
else
    echo "   ⚠️  Backend may still be starting up..."
fi

echo ""
echo "============================================"
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your app from anywhere:"
echo "   Frontend:  http://${SERVER_HOST}:${NGINX_PORT:-80}"
echo "   API Docs:  http://${SERVER_HOST}:${NGINX_PORT:-80}/docs"
echo "   Health:    http://${SERVER_HOST}:${NGINX_PORT:-80}/health"
echo ""
echo "📝 To seed data, run:"
echo "   docker compose exec backend python -m app.scripts.seed"
echo ""
echo "📋 To view logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 To stop:"
echo "   docker compose down"
echo "============================================"
