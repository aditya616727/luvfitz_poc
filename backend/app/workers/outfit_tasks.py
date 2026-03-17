"""
Outfit generation Celery tasks.
"""

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import logger
from app.services.outfit_service import OutfitService


@celery_app.task(name="app.workers.outfit_tasks.regenerate_outfits")
def regenerate_outfits(max_outfits: int = 100):
    """Delete existing outfits and regenerate fresh ones."""
    db = SessionLocal()
    try:
        service = OutfitService(db)
        deleted = service.delete_all()
        logger.info(f"Deleted {deleted} old outfits")

        generated = service.generate_outfits(max_outfits)
        logger.info(f"Generated {generated} new outfits")

        return {"deleted": deleted, "generated": generated}
    finally:
        db.close()


@celery_app.task(name="app.workers.outfit_tasks.generate_additional_outfits")
def generate_additional_outfits(max_outfits: int = 50):
    """Generate additional outfits without deleting existing ones."""
    db = SessionLocal()
    try:
        service = OutfitService(db)
        generated = service.generate_outfits(max_outfits)
        return {"generated": generated}
    finally:
        db.close()
