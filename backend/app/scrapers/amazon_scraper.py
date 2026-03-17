"""
Amazon US Scraper – scrapes real fashion products from amazon.com
Uses synchronous requests with rotating User-Agent headers to avoid bot
detection.  Parses HTML search-result pages with BeautifulSoup + lxml.
"""

import math
import re
import random
import time
import asyncio

import requests
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapedProduct
from app.core.logging import logger


# ---------------------------------------------------------------------------
# Rotating header sets – mimics real browser diversity
# ---------------------------------------------------------------------------
_HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                  "image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                       "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    },
]

_RESULTS_PER_PAGE = 20


class AmazonScraper(BaseScraper):
    SOURCE = "AMAZON"
    BASE_URL = "https://www.amazon.com"

    # (search_query, label, category_hint)
    SEARCH_QUERIES = [
        ("mens shirts",       "mens_shirts",       "TOP"),
        ("mens jeans",        "mens_pants",         "BOTTOM"),
        ("mens sneakers",     "mens_shoes",         "SHOE"),
        ("mens watches",      "mens_accessories",   "ACCESSORY"),
        ("womens tops",       "womens_tops",        "TOP"),
        ("womens jeans",      "womens_pants",       "BOTTOM"),
        ("womens shoes",      "womens_shoes",       "SHOE"),
        ("womens handbags",   "womens_accessories", "ACCESSORY"),
    ]

    # ------------------------------------------------------------------
    # Low-level helpers (synchronous – proven to bypass Amazon blocks)
    # ------------------------------------------------------------------
    @staticmethod
    def _get_headers() -> dict:
        return random.choice(_HEADERS_LIST)

    @staticmethod
    def _fetch_page(query: str, page: int, session: requests.Session):
        """Fetch one Amazon search-result page. Returns BeautifulSoup or None."""
        params = {"k": query, "page": page}
        headers = AmazonScraper._get_headers()
        # Force US locale via cookies so prices come back in USD
        cookies = {
            "lc-main": "en_US",
            "i18n-prefs": "USD",
            "sp-cdn": "\"L5Z9:IN\"",
        }
        try:
            resp = session.get(
                "https://www.amazon.com/s",
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=15,
            )
            if resp.status_code == 200:
                return BeautifulSoup(resp.content, "lxml")
            logger.warning(f"[Amazon] Non-200 status {resp.status_code} for page {page}")
            return None
        except requests.RequestException as e:
            logger.error(f"[Amazon] Request error on page {page}: {e}")
            return None

    @staticmethod
    def _extract_raw_products(soup: BeautifulSoup) -> list[dict]:
        """Parse raw product dicts from a search-result page."""
        products: list[dict] = []
        items = soup.find_all("div", {"data-component-type": "s-search-result"})

        for item in items:
            product: dict = {}

            # Title
            title_tag = item.find("h2")
            if title_tag:
                span = title_tag.find("span")
                product["title"] = (
                    span.get_text(strip=True) if span else title_tag.get_text(strip=True)
                )
            else:
                product["title"] = None

            # URL – try h2>a, then any /dp/ link, then construct from ASIN
            url = None
            if title_tag:
                a_tag = title_tag.find("a", href=True)
                if a_tag and a_tag.get("href"):
                    url = a_tag["href"]
            if not url:
                a_tag = item.find("a", href=True)
                if a_tag and a_tag.get("href") and "/dp/" in a_tag["href"]:
                    url = a_tag["href"]
            if not url:
                asin = item.get("data-asin")
                if asin:
                    url = f"/dp/{asin}"
            if url:
                product["url"] = (
                    f"https://www.amazon.com{url}" if url.startswith("/") else url
                )
            else:
                product["url"] = None

            # Price (offscreen span is the cleanest source)
            price_tag = item.find("span", {"class": "a-offscreen"})
            product["price"] = price_tag.get_text(strip=True) if price_tag else None

            # Image
            img_tag = item.find("img", {"class": "s-image"})
            product["image_url"] = img_tag["src"] if img_tag else None

            # ASIN
            product["asin"] = item.get("data-asin") or None

            # Brand – best-effort from a secondary line
            brand = ""
            for sel in [
                "span.a-size-base-plus.a-color-base",
                "h5 span",
            ]:
                brand_el = item.select_one(sel)
                if brand_el:
                    text = brand_el.get_text(strip=True)
                    if text and len(text) < 60:
                        brand = text
                        break
            product["brand"] = brand

            if product.get("title"):
                products.append(product)

        return products

    def _scrape_category_sync(
        self, query: str, label: str, count: int, session: requests.Session
    ) -> list[dict]:
        """Scrape up to *count* products for one query (synchronous)."""
        pages_needed = math.ceil(count / _RESULTS_PER_PAGE)
        all_products: list[dict] = []

        for page in range(1, pages_needed + 1):
            if len(all_products) >= count:
                break

            logger.info(f"[Amazon] {label} page {page} for '{query}'")
            soup = self._fetch_page(query, page, session)

            if soup is None:
                break

            # CAPTCHA / robot check
            if soup.find("form", {"action": "/errors/validateCaptcha"}):
                logger.warning("[Amazon] CAPTCHA detected – stopping this category.")
                break

            page_products = self._extract_raw_products(soup)
            if not page_products:
                logger.info(f"[Amazon] No products on page {page}, stopping.")
                break

            all_products.extend(page_products)

            if page < pages_needed:
                time.sleep(random.uniform(1.5, 3.5))

        return all_products[:count]

    # ------------------------------------------------------------------
    # Price parsing helper
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_price(raw: str | None) -> float:
        if not raw:
            return 0.0
        # Skip explicitly non-USD currencies
        if "₹" in raw or "INR" in raw or "€" in raw or "£" in raw:
            return 0.0
        match = re.search(r"\$?([\d,]+\.?\d*)", raw)
        if match:
            val = float(match.group(1).replace(",", ""))
            # Amazon may geo-locate to INR despite .com – INR fashion prices
            # are typically 500–10000₹ which look like $500-$10000 USD.
            # Real USD fashion rarely exceeds $500 on Amazon search pages.
            if val > 500:
                return 0.0
            return val
        return 0.0

    # ------------------------------------------------------------------
    # BaseScraper interface (async wrapper around sync requests)
    # ------------------------------------------------------------------
    async def scrape(self, max_products: int = 200) -> list[ScrapedProduct]:
        """Run the synchronous scraper in a thread so the event loop isn't blocked."""
        return await asyncio.to_thread(self._scrape_sync, max_products)

    def _scrape_sync(self, max_products: int) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        per_category = max(max_products // len(self.SEARCH_QUERIES), 10)

        session = requests.Session()

        for query, label, cat_hint in self.SEARCH_QUERIES:
            if len(products) >= max_products:
                break

            try:
                raw = self._scrape_category_sync(query, label, per_category, session)
                logger.info(f"[Amazon] {label}: raw {len(raw)} products")

                for item in raw:
                    price = self._parse_price(item.get("price"))
                    title = (item.get("title") or "")[:200]
                    url = item.get("url") or ""
                    image = item.get("image_url") or ""
                    brand = item.get("brand") or ""

                    if not title or price <= 0 or not url:
                        continue

                    products.append(
                        ScrapedProduct(
                            name=title,
                            price=price,
                            product_url=url,
                            source="AMAZON",
                            brand=brand,
                            image_url=image,
                            category_hint=cat_hint,
                        )
                    )
            except Exception as e:
                logger.error(f"[Amazon] Failed to scrape {label}: {e}")

            # Polite pause between categories
            time.sleep(random.uniform(2.0, 4.0))

        logger.info(f"[Amazon] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]
