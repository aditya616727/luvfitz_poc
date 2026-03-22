"""
SSENSE.com Scraper – powered by Scrapling.
Uses Scrapling's Selector for smart JSON-LD extraction and CSS-based fallback.
Falls back from Fetcher → StealthyFetcher → DynamicFetcher automatically.
"""

import re

from app.scrapers.base import BaseScraper, ScrapedProduct, css_first
from app.core.logging import logger


class SSENSEScraper(BaseScraper):
    SOURCE = "SSENSE"
    BASE_URL = "https://www.ssense.com"

    # SSENSE category pages with JSON-LD Product entries
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

    async def scrape(self, max_products: int = 300) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        per_category = max(max_products // len(self.CATEGORY_URLS), 15)

        for label, url, cat_hint in self.CATEGORY_URLS:
            try:
                adaptor = await self._fetch(url)
                if adaptor is None:
                    logger.error(f"[SSENSE] Failed to fetch {label}")
                    continue

                page_products = self._parse_products(adaptor, label, cat_hint)
                products.extend(page_products[:per_category])
                logger.info(f"[SSENSE] {label}: found {len(page_products)} products")
            except Exception as e:
                logger.error(f"[SSENSE] Failed to scrape {label}: {e}")

        logger.info(f"[SSENSE] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_products(self, adaptor, label: str, cat_hint: str) -> list[ScrapedProduct]:
        """
        Extract SSENSE products from JSON-LD and fallback HTML.
        Uses Scrapling's Adaptor for all parsing.
        """
        items: list[ScrapedProduct] = []

        # ── Primary: JSON-LD extraction ──
        jsonld_products = self._parse_jsonld(adaptor)

        for data in jsonld_products:
            try:
                name = data.get("name", "").strip()
                if not name:
                    continue

                brand = ""
                brand_data = data.get("brand", {})
                if isinstance(brand_data, dict):
                    brand = brand_data.get("name", "")
                elif isinstance(brand_data, str):
                    brand = brand_data

                offers = data.get("offers", {})
                try:
                    price = float(offers.get("price", 0))
                except (ValueError, TypeError):
                    price = 0.0

                currency = offers.get("priceCurrency", "USD")
                if currency != "USD":
                    continue

                image_url = data.get("image", "")
                if isinstance(image_url, list):
                    image_url = image_url[0] if image_url else ""

                raw_url = data.get("url", "") or offers.get("url", "")
                if raw_url and not raw_url.startswith("http"):
                    product_url = f"{self.BASE_URL}{raw_url}"
                else:
                    product_url = raw_url

                color = self._extract_color(name)
                description = data.get("description", "") or f"{brand} {name}"

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
            except (KeyError, TypeError) as e:
                logger.debug(f"[SSENSE] JSON-LD parse error: {e}")

        # ── Fallback: HTML scraping with Scrapling's smart selectors ──
        if not items:
            items = self._parse_html(adaptor, cat_hint)

        return items

    def _parse_html(self, adaptor, cat_hint: str) -> list[ScrapedProduct]:
        """Fallback HTML parsing using Scrapling's CSS selectors + auto-matching."""
        items: list[ScrapedProduct] = []

        product_cards = adaptor.css(
            "[data-testid*='product'], .product-tile, .plp-products__product"
        )

        for card in product_cards:
            try:
                brand_el = css_first(card, "[data-testid*='brand'], .product-brand, .brand")
                brand = brand_el.text.strip() if brand_el else ""

                name_el = css_first(card, "[data-testid*='name'], .product-name, .name")
                name = name_el.text.strip() if name_el else ""

                price_el = css_first(card, "[data-testid*='price'], .product-price, .price")
                price = 0.0
                if price_el:
                    match = re.search(r"[\d]+\.?\d*", price_el.text.replace(",", ""))
                    if match:
                        price = float(match.group())

                link_el = css_first(card, "a[href]")
                raw_url = link_el.attrib.get("href", "") if link_el else ""
                if raw_url and not raw_url.startswith("http"):
                    product_url = f"{self.BASE_URL}{raw_url}"
                else:
                    product_url = raw_url

                img_el = css_first(card, "img[src], img[data-src]")
                image_url = ""
                if img_el:
                    image_url = img_el.attrib.get("src", "") or img_el.attrib.get("data-src", "")

                color = self._extract_color(name)

                if name and price > 0 and product_url:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=round(price, 2),
                            product_url=product_url,
                            source="SSENSE",
                            brand=brand,
                            color=color,
                            description=f"{brand} {name}",
                            image_url=image_url,
                            category_hint=cat_hint,
                        )
                    )
            except Exception as e:
                logger.debug(f"[SSENSE] HTML parse error: {e}")

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
