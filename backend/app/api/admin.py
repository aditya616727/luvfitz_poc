"""
Admin API endpoints – trigger scraping, refresh, outfit generation.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.outfit_service import OutfitService
from app.workers.scrape_tasks import scrape_all, scrape_zappos, scrape_amazon, scrape_ssense
from app.workers.refresh_tasks import refresh_all_products
from app.workers.outfit_tasks import regenerate_outfits, generate_additional_outfits

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/scrape")
def trigger_scrape(
    source: str = Query("all", description="Source to scrape: all, zappos, amazon, ssense"),
    max_products: int = Query(200, ge=1, le=500),
):
    """Trigger scraping tasks."""
    source = source.lower()
    if source == "all":
        scrape_all.delay(max_products)
        return {"status": "all scrapers queued"}
    elif source == "zappos":
        scrape_zappos.delay(max_products)
        return {"status": "Zappos scraper queued"}
    elif source == "amazon":
        scrape_amazon.delay(max_products)
        return {"status": "Amazon scraper queued"}
    elif source == "ssense":
        scrape_ssense.delay(max_products)
        return {"status": "SSENSE scraper queued"}
    else:
        return {"error": f"Unknown source: {source}"}


@router.post("/refresh")
def trigger_refresh():
    """Trigger price & availability refresh for all products."""
    refresh_all_products.delay()
    return {"status": "refresh queued"}


@router.post("/generate-outfits")
def trigger_outfit_generation(
    max_outfits: int = Query(100, ge=1, le=1000),
    regenerate: bool = Query(False, description="Delete existing outfits before generating"),
    db: Session = Depends(get_db),
):
    """Generate outfit combinations."""
    if regenerate:
        regenerate_outfits.delay(max_outfits)
        return {"status": "outfit regeneration queued"}
    else:
        generate_additional_outfits.delay(max_outfits)
        return {"status": "outfit generation queued"}


@router.post("/generate-outfits-sync")
def trigger_outfit_generation_sync(
    max_outfits: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Generate outfit combinations synchronously (for development)."""
    service = OutfitService(db)
    generated = service.generate_outfits(max_outfits)
    return {"status": "done", "generated": generated}
