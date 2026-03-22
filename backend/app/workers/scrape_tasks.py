"""
Scraping Celery tasks – run scrapers and store products.
"""

import asyncio
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import logger
from app.services.product_service import ProductService
from app.scrapers.zappos_scraper import ZapposScraper
from app.scrapers.amazon_scraper import AmazonScraper
from app.scrapers.ssense_scraper import SSENSEScraper
from app.scrapers.hnm_scraper import HnmScraper


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.scrape_tasks.scrape_zappos", bind=True, max_retries=3)
def scrape_zappos(self, max_products: int = 200):
    logger.info("[Task] Starting Zappos scrape")
    try:
        scraper = ZapposScraper()
        products = _run_async(scraper.scrape_and_normalize(max_products))
        db = SessionLocal()
        try:
            service = ProductService(db)
            count = service.bulk_upsert([p.to_dict() for p in products])
            logger.info(f"[Task] Zappos: stored {count} products")
            return {"source": "ZAPPOS", "stored": count}
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"[Task] Zappos scrape failed: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.scrape_tasks.scrape_amazon", bind=True, max_retries=3)
def scrape_amazon(self, max_products: int = 100):
    logger.info("[Task] Starting Amazon scrape")
    try:
        scraper = AmazonScraper()
        products = _run_async(scraper.scrape_and_normalize(max_products))
        db = SessionLocal()
        try:
            service = ProductService(db)
            count = service.bulk_upsert([p.to_dict() for p in products])
            logger.info(f"[Task] Amazon: stored {count} products")
            return {"source": "AMAZON", "stored": count}
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"[Task] Amazon scrape failed: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.scrape_tasks.scrape_ssense", bind=True, max_retries=3)
def scrape_ssense(self, max_products: int = 200):
    logger.info("[Task] Starting SSENSE scrape")
    try:
        scraper = SSENSEScraper()
        products = _run_async(scraper.scrape_and_normalize(max_products))
        db = SessionLocal()
        try:
            service = ProductService(db)
            count = service.bulk_upsert([p.to_dict() for p in products])
            logger.info(f"[Task] SSENSE: stored {count} products")
            return {"source": "SSENSE", "stored": count}
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"[Task] SSENSE scrape failed: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.scrape_tasks.scrape_hnm", bind=True, max_retries=3)
def scrape_hnm(self, max_products: int = 200):
    logger.info("[Task] Starting H&M scrape")
    try:
        scraper = HnmScraper()
        products = _run_async(scraper.scrape_and_normalize(max_products))
        db = SessionLocal()
        try:
            service = ProductService(db)
            count = service.bulk_upsert([p.to_dict() for p in products])
            logger.info(f"[Task] H&M: stored {count} products")
            return {"source": "HNM", "stored": count}
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"[Task] H&M scrape failed: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.scrape_tasks.scrape_all")
def scrape_all(max_products_per_source: int = 200):
    """Trigger all scrapers."""
    logger.info("[Task] Triggering all scrapers")
    scrape_zappos.delay(max_products_per_source)
    scrape_amazon.delay(max_products_per_source)
    scrape_ssense.delay(max_products_per_source)
    scrape_hnm.delay(max_products_per_source)
    return {"status": "all scrapers triggered"}
