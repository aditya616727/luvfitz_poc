"""
Zappos.com Scraper – powered by Scrapling.
Uses Scrapling's Selector for smart CSS selection and JSON-LD extraction.
Falls back from Fetcher → StealthyFetcher → DynamicFetcher automatically.
"""

import re

from app.scrapers.base import BaseScraper, ScrapedProduct, css_first
from app.core.logging import logger


class ZapposScraper(BaseScraper):
    SOURCE = "ZAPPOS"
    BASE_URL = "https://www.zappos.com"

    # Zappos category pages – each returns ~100 JSON-LD Product entries
    # (label, url, category_hint)
    CATEGORY_URLS = [
        ("men-shirts", f"{BASE_URL}/men-shirts", "TOP"),
        ("men-pants", f"{BASE_URL}/men-pants", "BOTTOM"),
        ("men-sneakers", f"{BASE_URL}/men-sneakers", "SHOE"),
        ("men-accessories", f"{BASE_URL}/men-accessories", "ACCESSORY"),
        ("women-tops", f"{BASE_URL}/women-tops", "TOP"),
        ("women-pants", f"{BASE_URL}/women-pants", "BOTTOM"),
        ("women-sneakers", f"{BASE_URL}/women-sneakers", "SHOE"),
        ("women-accessories", f"{BASE_URL}/women-accessories", "ACCESSORY"),
    ]

    async def scrape(self, max_products: int = 300) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        per_category = max(max_products // len(self.CATEGORY_URLS), 20)

        for label, url, cat_hint in self.CATEGORY_URLS:
            try:
                adaptor = await self._fetch(url)
                if adaptor is None:
                    logger.error(f"[Zappos] Failed to fetch {label}")
                    continue

                page_products = self._parse_products(adaptor, label, cat_hint)
                products.extend(page_products[:per_category])
                logger.info(f"[Zappos] {label}: found {len(page_products)} products")
            except Exception as e:
                logger.error(f"[Zappos] Failed to scrape {label}: {e}")

        logger.info(f"[Zappos] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_products(self, adaptor, label: str, cat_hint: str) -> list[ScrapedProduct]:
        """
        Extract products from Zappos page using Scrapling's Adaptor.
        Primary: JSON-LD structured data. Fallback: HTML CSS selectors.
        """
        items: list[ScrapedProduct] = []

        # ── Primary: JSON-LD structured data ──
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

                color = data.get("color", "")
                if isinstance(color, list):
                    color = color[0] if color else ""

                description = data.get("description", "") or f"{brand} {name}"

                if name and price > 0 and product_url:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=round(price, 2),
                            product_url=product_url,
                            source="ZAPPOS",
                            brand=brand,
                            color=color,
                            description=description,
                            image_url=image_url,
                            category_hint=cat_hint,
                        )
                    )
            except (KeyError, TypeError) as e:
                logger.debug(f"[Zappos] Skipping product parse error: {e}")

        # ── Fallback: HTML scraping with Scrapling's smart CSS selectors ──
        if not items:
            items = self._parse_html(adaptor, cat_hint)

        return items

    def _parse_html(self, adaptor, cat_hint: str) -> list[ScrapedProduct]:
        """Fallback HTML parsing using Scrapling's CSS selectors + auto-matching."""
        items: list[ScrapedProduct] = []

        product_cards = adaptor.css("article[data-product-id]")
        if not product_cards:
            product_cards = adaptor.css("[itemtype*='Product']")
        if not product_cards:
            product_cards = adaptor.css(".product-card, .product")

        for card in product_cards:
            try:
                name_el = css_first(card, "span[itemprop='name'], .product-name, h3, h2")
                name = name_el.text.strip() if name_el else ""

                price_el = css_first(card,
                    "span[itemprop='price'], .product-price, span[class*='price']"
                )
                price = 0.0
                if price_el:
                    match = re.search(r"[\d]+\.?\d*", price_el.text.replace(",", ""))
                    if match:
                        price = float(match.group())

                brand_el = css_first(card, "span[itemprop='brand'], .brand-name")
                brand = brand_el.text.strip() if brand_el else ""

                link_el = css_first(card, "a[href]")
                raw_url = link_el.attrib.get("href", "") if link_el else ""
                if raw_url and not raw_url.startswith("http"):
                    product_url = f"{self.BASE_URL}{raw_url}"
                else:
                    product_url = raw_url

                img_el = css_first(card, "img[src]")
                image_url = img_el.attrib.get("src", "") if img_el else ""

                if name and price > 0 and product_url:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=round(price, 2),
                            product_url=product_url,
                            source="ZAPPOS",
                            brand=brand,
                            image_url=image_url,
                            category_hint=cat_hint,
                        )
                    )
            except Exception as e:
                logger.debug(f"[Zappos] HTML parse error: {e}")

        return items
