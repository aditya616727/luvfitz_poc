"""
Base scraper interface and shared utilities.
Powered by Scrapling – high-performance scraping with anti-bot stealth.

Scrapling v0.4+ provides three fetcher types used in a tiered fallback strategy:
  1. Fetcher          – lightweight HTTP via curl_cffi (fastest, least stealth)
  2. StealthyFetcher  – real browser via Camoufox/Firefox (best anti-bot)
  3. DynamicFetcher   – Playwright with stealth patches (last resort)

Response objects are Selector/Adaptor instances that support:
  - .css(selector)     → list of Selectors
  - .find(tag)         → first matching Selector
  - .text              → inner text content
  - .attrib            → element attributes dict
  - .xpath(query)      → XPath-based selection

Reference: https://scrapling.readthedocs.io/en/latest/
"""

import asyncio
import json
import random
from abc import ABC, abstractmethod
from typing import Optional

from scrapling import Fetcher, StealthyFetcher, DynamicFetcher

from app.core.config import get_settings
from app.core.logging import logger
from app.utils.taxonomy import map_taxonomy, extract_style_tags, get_google_taxonomy_id, get_fallback_google_taxonomy

settings = get_settings()


# ---------------------------------------------------------------------------
# Helper: css_first (scrapling v0.4 has .css() returning a list, no .css_first)
# ---------------------------------------------------------------------------
def css_first(element, selector: str):
    """Return the first CSS match on *element*, or None."""
    results = element.css(selector)
    return results[0] if results else None


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
            cat = self.category_hint
            google_tax, tax_id = get_fallback_google_taxonomy(self.category_hint)

        self.category = cat
        self.taxonomy = google_tax
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
    """
    Abstract base class for all retailer scrapers.
    Uses Scrapling's tiered fetcher strategy with automatic fallback.

    The response from any fetcher is a Selector that supports .css(), .text, .attrib, etc.
    """

    SOURCE: str = ""

    # Override in subclass to use StealthyFetcher by default (e.g. Amazon)
    USE_STEALTHY_BY_DEFAULT: bool = False

    def __init__(self):
        self.settings = get_settings()
        self._fetcher = Fetcher()
        self._stealthy_fetcher = None   # Lazy init – heavy resource
        self._dynamic_fetcher = None    # Lazy init – heavy resource

    def _get_stealthy_fetcher(self) -> StealthyFetcher:
        """Lazily initialize StealthyFetcher (Camoufox-based real Firefox browser)."""
        if self._stealthy_fetcher is None:
            self._stealthy_fetcher = StealthyFetcher()
        return self._stealthy_fetcher

    def _get_dynamic_fetcher(self) -> DynamicFetcher:
        """Lazily initialize DynamicFetcher (Playwright with stealth patches)."""
        if self._dynamic_fetcher is None:
            self._dynamic_fetcher = DynamicFetcher()
        return self._dynamic_fetcher

    async def _fetch(self, url: str, use_stealthy: bool = False):
        """
        Fetch a URL with tiered fallback strategy.

        Returns a Scrapling Response (which is a Selector) that supports:
          - .css(selector)   → list of child Selectors
          - .find(tag)       → first matching Selector
          - .text            → inner text content
          - .attrib          → element attributes dict
          - .xpath(query)    → XPath-based selection

        Use css_first(element, selector) helper for first-match convenience.
        Returns None if all fetchers fail.
        """
        delay = self.settings.scrape_delay_seconds + random.uniform(0, 1)
        await asyncio.sleep(delay)

        # Tier 1: Fast HTTP Fetcher (or StealthyFetcher if configured)
        if use_stealthy or self.USE_STEALTHY_BY_DEFAULT:
            return await self._fetch_stealthy(url)

        try:
            response = await asyncio.to_thread(
                self._fetcher.get,
                url,
                stealthy_headers=True,
                follow_redirects=True,
            )
            if response.status == 200:
                logger.debug(f"[{self.SOURCE}] Fetcher OK: {url}")
                return response
            else:
                logger.warning(
                    f"[{self.SOURCE}] Fetcher returned {response.status} for {url}, trying StealthyFetcher"
                )
                return await self._fetch_stealthy(url)
        except Exception as e:
            logger.warning(f"[{self.SOURCE}] Fetcher failed for {url}: {e}, trying StealthyFetcher")
            return await self._fetch_stealthy(url)

    async def _fetch_stealthy(self, url: str):
        """Tier 2: Use StealthyFetcher (real Camoufox/Firefox browser)."""
        try:
            fetcher = self._get_stealthy_fetcher()
            response = await asyncio.to_thread(
                fetcher.fetch,
                url,
                headless=True,
                block_images=True,
                disable_resources=True,
            )
            if response.status == 200:
                logger.debug(f"[{self.SOURCE}] StealthyFetcher OK: {url}")
                return response
            else:
                logger.warning(
                    f"[{self.SOURCE}] StealthyFetcher returned {response.status} for {url}"
                )
                return await self._fetch_dynamic(url)
        except Exception as e:
            logger.warning(
                f"[{self.SOURCE}] StealthyFetcher failed for {url}: {e}, trying DynamicFetcher"
            )
            return await self._fetch_dynamic(url)

    async def _fetch_dynamic(self, url: str):
        """Tier 3: Last resort – DynamicFetcher with stealth patches."""
        try:
            fetcher = self._get_dynamic_fetcher()
            response = await asyncio.to_thread(
                fetcher.fetch,
                url,
                headless=True,
                disable_webgl=True,
                block_images=True,
            )
            if response.status == 200:
                logger.debug(f"[{self.SOURCE}] DynamicFetcher OK: {url}")
                return response
            logger.error(f"[{self.SOURCE}] All fetchers failed for {url}")
            return None
        except Exception as e:
            logger.error(f"[{self.SOURCE}] DynamicFetcher failed for {url}: {e}")
            return None

    def _parse_jsonld(self, response) -> list[dict]:
        """
        Extract JSON-LD Product data from a Scrapling response/Selector.
        """
        items = []
        scripts = response.css('script[type="application/ld+json"]')

        for script in scripts:
            try:
                text = script.text
                if not text:
                    continue
                data = json.loads(text)

                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            items.append(item)
                elif isinstance(data, dict):
                    if data.get("@type") == "Product":
                        items.append(data)
                    elif "@graph" in data:
                        for item in data["@graph"]:
                            if isinstance(item, dict) and item.get("@type") == "Product":
                                items.append(item)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"[{self.SOURCE}] JSON-LD parse error: {e}")

        return items

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
                logger.warning(f"[{self.SOURCE}] Skipping unclassified product: {p.name}")
        logger.info(f"[{self.SOURCE}] Scraped {len(normalized)}/{len(products)} products after normalization")
        return normalized
