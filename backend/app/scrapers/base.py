"""
Base scraper interface and shared utilities.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import logger
from app.utils.taxonomy import map_taxonomy, extract_style_tags, get_google_taxonomy_id, get_fallback_google_taxonomy

settings = get_settings()


class ScrapedProduct:
    """Intermediate representation of a scraped product."""

    def __init__(
        self,
        name: str,
        price: float,
        product_url: str,
        source: str,
        brand: str = "",
        color: str = "",
        description: str = "",
        image_url: str = "",
        category_hint: str = "",
    ):
        self.name = name
        self.price = price
        self.product_url = product_url
        self.source = source
        self.brand = brand
        self.color = color
        self.description = description
        self.image_url = image_url
        self.category_hint = category_hint  # e.g. "TOP", "BOTTOM", "SHOE", "ACCESSORY"
        self.category: Optional[str] = None
        self.taxonomy: Optional[str] = None
        self.google_product_category: Optional[str] = None
        self.google_taxonomy_id: Optional[int] = None
        self.style_tags: list[str] = []
        self.availability: bool = True

    def normalize(self) -> "ScrapedProduct":
        """Apply Google Product Taxonomy mapping and style tags. Falls back to category_hint."""
        cat, google_tax = map_taxonomy(self.name, self.description)
        tax_id = get_google_taxonomy_id(self.name, self.description)

        if cat is None and self.category_hint:
            # Use the category hint from the URL/page being scraped
            cat = self.category_hint
            google_tax, tax_id = get_fallback_google_taxonomy(self.category_hint)

        self.category = cat
        self.taxonomy = google_tax  # keep backward compat: taxonomy = google path
        self.google_product_category = google_tax
        self.google_taxonomy_id = tax_id
        self.style_tags = extract_style_tags(self.name, self.description, self.color)
        return self

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "product_url": self.product_url,
            "source": self.source,
            "brand": self.brand,
            "color": self.color,
            "description": self.description,
            "image_url": self.image_url,
            "category": self.category,
            "taxonomy": self.taxonomy,
            "google_product_category": self.google_product_category,
            "google_taxonomy_id": self.google_taxonomy_id,
            "style_tags": self.style_tags,
            "availability": self.availability,
        }


class BaseScraper(ABC):
    """Abstract base class for all retailer scrapers."""

    SOURCE: str = ""

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "User-Agent": self.settings.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch(self, url: str, client: httpx.AsyncClient) -> str:
        """Fetch a URL with retries and polite delays."""
        delay = self.settings.scrape_delay_seconds + random.uniform(0, 1)
        await asyncio.sleep(delay)
        response = await client.get(url, headers=self.headers, follow_redirects=True, timeout=30)
        response.raise_for_status()
        return response.text

    @abstractmethod
    async def scrape(self, max_products: int = 100) -> list[ScrapedProduct]:
        """Scrape products from the retailer. Must be implemented by subclasses."""
        ...

    async def scrape_and_normalize(self, max_products: int = 100) -> list[ScrapedProduct]:
        """Scrape products and apply normalization."""
        products = await self.scrape(max_products)
        normalized = []
        for p in products:
            p.normalize()
            if p.category is not None:
                normalized.append(p)
            else:
                logger.warning(f"Skipping unclassified product: {p.name}")
        logger.info(f"[{self.SOURCE}] Scraped {len(normalized)}/{len(products)} products after normalization")
        return normalized
