"""
SSENSE.com Scraper – scrapes real luxury/designer fashion products from ssense.com
Uses JSON-LD structured data embedded in category listing pages.
Each category page provides ~120 products with full schema.org Product data.
"""

import json

from bs4 import BeautifulSoup
import httpx

from app.scrapers.base import BaseScraper, ScrapedProduct
from app.core.logging import logger


class SSENSEScraper(BaseScraper):
    SOURCE = "SSENSE"
    BASE_URL = "https://www.ssense.com"

    # SSENSE category pages – each returns ~120 JSON-LD Product entries
    # (label, url, category_hint)
    CATEGORY_URLS = [
        ("men-tshirts", f"{BASE_URL}/en-us/men/t-shirts", "TOP"),
        ("men-shirts", f"{BASE_URL}/en-us/men/shirts", "TOP"),
        ("men-pants", f"{BASE_URL}/en-us/men/pants", "BOTTOM"),
        ("men-shoes", f"{BASE_URL}/en-us/men/shoes", "SHOE"),
        ("men-accessories", f"{BASE_URL}/en-us/men/accessories", "ACCESSORY"),
        ("women-tops", f"{BASE_URL}/en-us/women/tops", "TOP"),
        ("women-pants", f"{BASE_URL}/en-us/women/pants", "BOTTOM"),
        ("women-shoes", f"{BASE_URL}/en-us/women/shoes", "SHOE"),
        ("women-accessories", f"{BASE_URL}/en-us/women/accessories", "ACCESSORY"),
    ]

    async def scrape(self, max_products: int = 100) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        per_category = max(max_products // len(self.CATEGORY_URLS), 15)

        async with httpx.AsyncClient() as client:
            for label, url, cat_hint in self.CATEGORY_URLS:
                try:
                    html = await self._fetch(url, client)
                    page_products = self._parse_jsonld(html, label, cat_hint)
                    # Limit per category for even distribution
                    products.extend(page_products[:per_category])
                    logger.info(f"[SSENSE] {label}: found {len(page_products)} products")
                except Exception as e:
                    logger.error(f"[SSENSE] Failed to scrape {label}: {e}")

        logger.info(f"[SSENSE] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_jsonld(self, html: str, label: str, cat_hint: str = "") -> list[ScrapedProduct]:
        """Extract products from JSON-LD script tags."""
        soup = BeautifulSoup(html, "html.parser")
        items: list[ScrapedProduct] = []

        ld_scripts = soup.select('script[type="application/ld+json"]')

        for script in ld_scripts:
            try:
                data = json.loads(script.string)
                if data.get("@type") != "Product":
                    continue

                name = data.get("name", "").strip()
                brand = ""
                brand_data = data.get("brand", {})
                if isinstance(brand_data, dict):
                    brand = brand_data.get("name", "")
                elif isinstance(brand_data, str):
                    brand = brand_data

                # Price from offers
                offers = data.get("offers", {})
                price_val = offers.get("price", 0)
                try:
                    price = float(price_val)
                except (ValueError, TypeError):
                    price = 0.0

                # Currency check – only USD
                currency = offers.get("priceCurrency", "USD")
                if currency != "USD":
                    continue

                # Image URL
                image_url = data.get("image", "")

                # Product URL
                raw_url = data.get("url", "") or offers.get("url", "")
                if raw_url and not raw_url.startswith("http"):
                    product_url = f"{self.BASE_URL}{raw_url}"
                else:
                    product_url = raw_url

                # Extract color from product name (SSENSE includes color in name like "Blue Denim Jacket")
                color = self._extract_color(name)

                # Description from brand + name
                description = f"{brand} {name}" if brand else name

                if name and price > 0 and product_url:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=round(price, 2),
                            product_url=product_url,
                            source="SSENSE",
                            brand=brand,
                            color=color,
                            description=description,
                            image_url=image_url,
                            category_hint=cat_hint,
                        )
                    )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"[SSENSE] Skipping JSON-LD parse error: {e}")

        return items

    @staticmethod
    def _extract_color(name: str) -> str:
        """Extract color from product name – SSENSE names often start with color."""
        colors = [
            "black", "white", "red", "blue", "green", "yellow", "pink",
            "purple", "orange", "brown", "gray", "grey", "navy", "beige",
            "cream", "olive", "maroon", "tan", "gold", "silver", "khaki",
            "burgundy", "charcoal", "taupe", "ivory", "coral", "teal",
            "indigo", "multicolor", "multi",
        ]
        name_lower = name.lower()
        for color in colors:
            if name_lower.startswith(color) or f" {color} " in f" {name_lower} ":
                return color.capitalize()
        return ""
