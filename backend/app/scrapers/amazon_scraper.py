"""
Amazon US Scraper – powered by Scrapling with StealthyFetcher (Camoufox).
Amazon has aggressive bot detection; StealthyFetcher uses a real Firefox browser
via Camoufox to bypass CAPTCHAs and fingerprint checks.
"""

import re
import math
import random
import asyncio
from typing import Optional

from app.scrapers.base import BaseScraper, ScrapedProduct, css_first
from app.core.logging import logger


class AmazonScraper(BaseScraper):
    SOURCE = "AMAZON"
    BASE_URL = "https://www.amazon.com"

    # Use StealthyFetcher by default – Amazon blocks simple HTTP fetchers
    USE_STEALTHY_BY_DEFAULT = True

    # (search_query, label, category_hint)
    SEARCH_QUERIES = [
        ("mens shirts", "mens_shirts", "TOP"),
        ("mens jeans", "mens_pants", "BOTTOM"),
        ("mens sneakers", "mens_shoes", "SHOE"),
        ("mens watches", "mens_accessories", "ACCESSORY"),
        ("womens tops", "womens_tops", "TOP"),
        ("womens jeans", "womens_pants", "BOTTOM"),
        ("womens shoes", "womens_shoes", "SHOE"),
        ("womens handbags", "womens_accessories", "ACCESSORY"),
    ]

    async def scrape(self, max_products: int = 200) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        per_category = max(max_products // len(self.SEARCH_QUERIES), 10)

        for query, label, cat_hint in self.SEARCH_QUERIES:
            if len(products) >= max_products:
                break

            try:
                category_products = await self._scrape_category(
                    query, label, cat_hint, per_category
                )
                products.extend(category_products)
                logger.info(f"[Amazon] {label}: found {len(category_products)} products")
            except Exception as e:
                logger.error(f"[Amazon] Failed to scrape {label}: {e}")

            # Polite pause between categories
            await asyncio.sleep(random.uniform(2.0, 4.0))

        logger.info(f"[Amazon] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    async def _scrape_category(
        self, query: str, label: str, cat_hint: str, count: int
    ) -> list[ScrapedProduct]:
        """Scrape one Amazon search category using Scrapling's StealthyFetcher."""
        results_per_page = 20
        pages_needed = math.ceil(count / results_per_page)
        all_products: list[ScrapedProduct] = []

        for page in range(1, pages_needed + 1):
            if len(all_products) >= count:
                break

            url = f"{self.BASE_URL}/s?k={query.replace(' ', '+')}&page={page}"
            logger.info(f"[Amazon] {label} page {page}: {url}")

            adaptor = await self._fetch(url, use_stealthy=True)
            if adaptor is None:
                break

            # Check for CAPTCHA using Scrapling selectors
            captcha = css_first(adaptor, "form[action*='validateCaptcha']")
            if captcha:
                logger.warning("[Amazon] CAPTCHA detected – stopping this category.")
                break

            # Log page diagnostics for debugging (helpful when selectors don't match)
            result_cards = adaptor.css("div[data-component-type='s-search-result']")
            if not result_cards:
                page_text = (adaptor.text or "")[:300]
                logger.warning(
                    f"[Amazon] No search-result divs found on page {page}. "
                    f"Page text preview: {page_text!r}"
                )

            page_products = self._extract_products(adaptor, cat_hint)
            if not page_products:
                logger.info(f"[Amazon] No products on page {page}, stopping.")
                break

            all_products.extend(page_products)

            if page < pages_needed:
                await asyncio.sleep(random.uniform(1.5, 3.5))

        return all_products[:count]

    def _extract_products(self, response, cat_hint: str) -> list[ScrapedProduct]:
        """
        Extract products from Amazon search results using Scrapling selectors.
        Tries multiple selector strategies to handle different page layouts
        (bot-detected pages, mobile layouts, regional variants).
        """
        items: list[ScrapedProduct] = []

        # Strategy 1: Standard search result cards
        result_cards = response.css("div[data-component-type='s-search-result']")

        # Strategy 2: Alternate layout (some bot-mitigated pages)
        if not result_cards:
            result_cards = response.css("div.s-result-item[data-asin]")

        # Strategy 3: Broader fallback
        if not result_cards:
            result_cards = response.css("[data-asin]")
            # Filter out non-product elements (e.g. ads container)
            result_cards = [c for c in result_cards if c.attrib.get("data-asin", "").strip()]

        for card in result_cards:
            try:
                # Title
                title_el = css_first(card, "h2 span")
                if not title_el:
                    title_el = css_first(card, "h2")
                title = title_el.text.strip()[:200] if title_el else ""

                if not title:
                    continue

                # URL
                url = ""
                link_el = css_first(card, "h2 a[href]")
                if link_el:
                    href = link_el.attrib.get("href", "")
                    if href:
                        url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

                if not url:
                    asin = card.attrib.get("data-asin", "")
                    if asin:
                        url = f"{self.BASE_URL}/dp/{asin}"

                if not url:
                    continue

                # Price
                price_el = css_first(card, "span.a-offscreen")
                price = self._parse_price(price_el.text if price_el else None)

                if price <= 0:
                    continue

                # Image
                img_el = css_first(card, "img.s-image")
                image_url = img_el.attrib.get("src", "") if img_el else ""

                # Brand
                brand = ""
                for sel in [
                    "span.a-size-base-plus.a-color-base",
                    "h5 span",
                ]:
                    brand_el = css_first(card, sel)
                    if brand_el:
                        text = brand_el.text.strip()
                        if text and len(text) < 60:
                            brand = text
                            break

                items.append(
                    ScrapedProduct(
                        name=title,
                        price=price,
                        product_url=url,
                        source="AMAZON",
                        brand=brand,
                        image_url=image_url,
                        category_hint=cat_hint,
                    )
                )
            except Exception as e:
                logger.debug(f"[Amazon] Product parse error: {e}")

        return items

    @staticmethod
    def _parse_price(raw: Optional[str]) -> float:
        """Parse price string to float, filtering non-USD and outliers."""
        if not raw:
            return 0.0
        if "₹" in raw or "INR" in raw or "€" in raw or "£" in raw:
            return 0.0
        match = re.search(r"\$?([\d,]+\.?\d*)", raw)
        if match:
            val = float(match.group(1).replace(",", ""))
            if val > 500:
                return 0.0
            return val
        return 0.0
