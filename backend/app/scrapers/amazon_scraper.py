"""
Amazon US Scraper – scrapes real fashion products from amazon.com
Uses search result pages for fashion categories with HTML parsing.
Extracts product name, price, image, brand from search result cards.
"""

import re
from bs4 import BeautifulSoup
import httpx

from app.scrapers.base import BaseScraper, ScrapedProduct
from app.core.logging import logger


class AmazonScraper(BaseScraper):
    SOURCE = "AMAZON"
    BASE_URL = "https://www.amazon.com"

    # Simpler search queries that return more consistent results
    # (query_path, label, category_hint)
    SEARCH_QUERIES = [
        ("s?k=mens+shirts&i=fashion", "mens_shirts", "TOP"),
        ("s?k=mens+jeans&i=fashion", "mens_pants", "BOTTOM"),
        ("s?k=mens+sneakers&i=fashion", "mens_shoes", "SHOE"),
        ("s?k=mens+watches&i=fashion", "mens_accessories", "ACCESSORY"),
        ("s?k=womens+tops&i=fashion", "womens_tops", "TOP"),
        ("s?k=womens+jeans&i=fashion", "womens_pants", "BOTTOM"),
        ("s?k=womens+shoes&i=fashion", "womens_shoes", "SHOE"),
        ("s?k=womens+handbags&i=fashion", "womens_accessories", "ACCESSORY"),
    ]

    def __init__(self):
        super().__init__()
        self.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    async def scrape(self, max_products: int = 100) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []

        async with httpx.AsyncClient() as client:
            for query_path, label, cat_hint in self.SEARCH_QUERIES:
                if len(products) >= max_products:
                    break

                url = f"{self.BASE_URL}/{query_path}"
                try:
                    html = await self._fetch(url, client)
                    page_products = self._parse_search_results(html, cat_hint)
                    products.extend(page_products)
                    logger.info(f"[Amazon] {label}: found {len(page_products)} products")
                except Exception as e:
                    logger.error(f"[Amazon] Failed to scrape {label}: {e}")

        logger.info(f"[Amazon] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_search_results(self, html: str, cat_hint: str = "") -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        items = []

        results = soup.select("div[data-component-type='s-search-result']")

        for result in results:
            try:
                asin = result.get("data-asin", "")
                if not asin:
                    continue

                # Name – try multiple selectors
                name = ""
                for sel in ["h2 span.a-text-normal", "h2 a span", "h2"]:
                    name_el = result.select_one(sel)
                    if name_el:
                        text = name_el.get_text(strip=True)
                        if text:
                            name = text
                            break

                # Price – comprehensive extraction
                price = self._extract_price(result)

                # Image
                img_el = result.select_one("img.s-image")
                image_url = img_el.get("src", "") if img_el else ""

                # Brand
                brand = self._extract_brand(result)

                # Product URL – always use ASIN for reliable URL
                product_url = f"{self.BASE_URL}/dp/{asin}"

                # Skip products missing essential data
                if not name or not image_url:
                    continue

                # Accept products even without price (some have price hidden)
                if price <= 0:
                    continue

                items.append(
                    ScrapedProduct(
                        name=name[:200],
                        price=price,
                        product_url=product_url,
                        source="AMAZON",
                        brand=brand,
                        image_url=image_url,
                        category_hint=cat_hint,
                    )
                )
            except Exception as e:
                logger.debug(f"[Amazon] Skipping result parse error: {e}")

        return items

    @staticmethod
    def _extract_price(result) -> float:
        """Extract price from Amazon search result card with multiple strategies."""
        # Strategy 1: offscreen price text (cleanest)
        offscreen = result.select_one("span.a-offscreen")
        if offscreen:
            text = offscreen.get_text(strip=True)
            # Handle both $ and INR/other currency prefixes
            match = re.search(r"[\$]?([\d,]+\.?\d*)", text)
            if match:
                val = float(match.group(1).replace(",", ""))
                # Skip non-USD (INR prices are typically > 500 for clothes)
                if "INR" in text or "₹" in text:
                    return 0.0
                return val

        # Strategy 2: a-price whole + fraction
        price_el = result.select_one("span.a-price:not(.a-text-price)")
        if price_el:
            whole_el = price_el.select_one("span.a-price-whole")
            frac_el = price_el.select_one("span.a-price-fraction")
            if whole_el:
                whole = whole_el.get_text(strip=True).rstrip(".").replace(",", "")
                frac = frac_el.get_text(strip=True) if frac_el else "00"
                try:
                    return float(f"{whole}.{frac}")
                except ValueError:
                    pass

        # Strategy 3: any price-like text in the card
        price_text = result.select_one("span.a-price")
        if price_text:
            text = price_text.get_text(strip=True)
            match = re.search(r"\$([\d,]+\.?\d*)", text)
            if match:
                return float(match.group(1).replace(",", ""))

        return 0.0

    @staticmethod
    def _extract_brand(result) -> str:
        """Extract brand from Amazon result."""
        for sel in [
            "span.a-size-base-plus.a-color-base",
            "h2 + div span.a-size-base",
            "h5 span",
        ]:
            brand_el = result.select_one(sel)
            if brand_el:
                text = brand_el.get_text(strip=True)
                if text and len(text) < 60:
                    return text
        return ""
