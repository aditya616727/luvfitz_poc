"""
Price & availability refresh Celery tasks – powered by Scrapling.
Runs daily to keep product data fresh.
Uses Fetcher for lightweight sites, StealthyFetcher for Amazon.
"""

import asyncio
import re
from datetime import datetime, timezone

from scrapling import Fetcher, StealthyFetcher

from app.scrapers.base import css_first
from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import logger
from app.models.models import Product


# ── Lazy-initialised fetchers (reused across tasks) ──
_fetcher: Fetcher | None = None
_stealthy: StealthyFetcher | None = None


def _get_fetcher() -> Fetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = Fetcher()
    return _fetcher


def _get_stealthy() -> StealthyFetcher:
    global _stealthy
    if _stealthy is None:
        _stealthy = StealthyFetcher()
    return _stealthy


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _fetch_product_page(url: str, source: str):
    """
    Fetch a product page via Scrapling.
    Amazon requires StealthyFetcher; Zappos / SSENSE use plain Fetcher first.
    Returns a Scrapling Response (Selector) or None.
    """
    use_stealthy = source.upper() == "AMAZON"

    try:
        if use_stealthy:
            response = _get_stealthy().fetch(url)
        else:
            response = _get_fetcher().get(url, stealthy_headers=True, follow_redirects=True)

        if response.status == 200:
            return response
        elif response.status == 404:
            return None
        else:
            logger.warning(f"Refresh fetch got {response.status} for {url}")
            # Fallback to stealthy if basic fetcher failed
            if not use_stealthy:
                response = _get_stealthy().fetch(url)
                if response.status == 200:
                    return response
            return None
    except Exception as e:
        logger.error(f"Refresh fetch error for {url}: {e}")
        return None


def _extract_price(response, source: str) -> float | None:
    """Extract price from product page using Scrapling CSS selectors."""
    price_selectors = {
        "ZAPPOS": ["span[itemprop='price']", "span.a-offscreen", "span[class*='price']"],
        "AMAZON": ["span.a-price .a-offscreen", "#priceblock_ourprice", ".a-price-whole"],
        "SSENSE": ["span[itemprop='price']", "span[class*='price']", ".price"],
        "HNM": ["span.price-value", "span[class*='price']", ".product-price", "span[itemprop='price']"],
    }

    selectors = price_selectors.get(source, ["span[class*='price']", ".price"])

    for selector in selectors:
        el = css_first(response, selector)
        if el:
            text = el.text.strip()
            match = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
            if match:
                return float(match.group())

    return None


def _check_availability(response) -> bool:
    """Check if product is in stock from the page content."""
    page_text = response.text.lower() if response.text else ""

    out_of_stock_signals = [
        "out of stock",
        "currently unavailable",
        "sold out",
        "not available",
        "no longer available",
    ]

    for signal in out_of_stock_signals:
        if signal in page_text:
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

        response = _run_async(_fetch_product_page(product.product_url, product.source.value))

        if response is None:
            # Product page gone – mark as unavailable
            product.availability = False
            product.last_updated = datetime.now(timezone.utc)
            db.commit()
            return {"status": "unavailable", "product_id": product_id}

        # Extract price
        new_price = _extract_price(response, product.source.value)
        if new_price and new_price > 0:
            product.price = new_price

        # Check availability
        product.availability = _check_availability(response)
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
