"""
Price & availability refresh Celery tasks.
Runs daily to keep product data fresh.
"""

import asyncio
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.core.logging import logger
from app.models.models import Product

settings = get_settings()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _fetch_product_page(url: str) -> str | None:
    """Fetch a product page with error handling."""
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=20)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                return None  # Product removed
            else:
                logger.warning(f"Refresh fetch got {response.status_code} for {url}")
                return None
    except Exception as e:
        logger.error(f"Refresh fetch error for {url}: {e}")
        return None


def _extract_price_from_html(html: str, source: str) -> float | None:
    """Extract price from product page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    price_selectors = {
        "ZAPPOS": ["span[itemprop='price']", "span.a-offscreen", "span[class*='price']"],
        "AMAZON": ["span.a-price .a-offscreen", "#priceblock_ourprice", ".a-price-whole"],
        "SSENSE": ["span[itemprop='price']", "span[class*='price']", ".price"],
    }

    selectors = price_selectors.get(source, ["span[class*='price']", ".price"])

    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            match = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
            if match:
                return float(match.group())

    return None


def _check_availability(html: str, source: str) -> bool:
    """Check if product is in stock from the page HTML."""
    html_lower = html.lower()

    out_of_stock_signals = [
        "out of stock",
        "currently unavailable",
        "sold out",
        "not available",
        "no longer available",
    ]

    for signal in out_of_stock_signals:
        if signal in html_lower:
            return False

    return True


@celery_app.task(name="app.workers.refresh_tasks.refresh_product", bind=True, max_retries=2)
def refresh_product(self, product_id: str):
    """Refresh a single product's price and availability."""
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            logger.warning(f"Product {product_id} not found for refresh")
            return {"status": "not_found"}

        html = _run_async(_fetch_product_page(product.product_url))

        if html is None:
            # Product page gone – mark as unavailable
            product.availability = False
            product.last_updated = datetime.now(timezone.utc)
            db.commit()
            return {"status": "unavailable", "product_id": product_id}

        # Extract price
        new_price = _extract_price_from_html(html, product.source.value)
        if new_price and new_price > 0:
            product.price = new_price

        # Check availability
        product.availability = _check_availability(html, product.source.value)
        product.last_updated = datetime.now(timezone.utc)

        db.commit()
        logger.info(f"Refreshed {product.name}: ${product.price}, available={product.availability}")
        return {
            "status": "refreshed",
            "product_id": product_id,
            "price": product.price,
            "available": product.availability,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Refresh failed for {product_id}: {exc}")
        self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task(name="app.workers.refresh_tasks.refresh_all_products")
def refresh_all_products():
    """Queue refresh tasks for all products."""
    db = SessionLocal()
    try:
        products = db.query(Product.id).filter(Product.availability == True).all()
        logger.info(f"Queuing refresh for {len(products)} products")

        for (product_id,) in products:
            refresh_product.delay(str(product_id))

        return {"status": "queued", "count": len(products)}
    finally:
        db.close()
