"""
Mini Outfit Builder – FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.logging import logger
from app.api import products, outfits, admin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan – create tables on startup."""
    logger.info("Starting Mini Outfit Builder API")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    yield
    logger.info("Shutting down Mini Outfit Builder API")


app = FastAPI(
    title="Mini Outfit Builder API",
    description=(
        "Fashion outfit generation system that scrapes products from Zappos, Amazon, "
        "SSENSE, and H&M, then creates styled outfits searchable by vibe."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://frontend:3000",
        "*",  # Remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(products.router, prefix="/api")
app.include_router(outfits.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Mini Outfit Builder API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.app_env,
    }
