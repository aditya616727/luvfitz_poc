"""
H&M (hm.com) Scraper – powered by Scrapling.
Scrapes product listing pages from H&M US store.
Uses JSON-LD when available, falls back to HTML product card parsing.
H&M product pages embed product data in structured HTML with clear CSS selectors.
"""

import re

from app.scrapers.base import BaseScraper, ScrapedProduct, css_first
from app.core.logging import logger


class HnmScraper(BaseScraper):
    SOURCE = "HNM"
    BASE_URL = "https://www2.hm.com"

    # H&M renders products via JavaScript – needs a real browser
    USE_STEALTHY_BY_DEFAULT = True

    # H&M US category listing pages
    # (label, url, category_hint)
    CATEGORY_URLS = [
        # Men
        ("men-tshirts", f"{BASE_URL}/en_us/men/products/t-shirts-tank-tops.html", "TOP"),
        ("men-shirts", f"{BASE_URL}/en_us/men/products/shirts.html", "TOP"),
        ("men-jeans", f"{BASE_URL}/en_us/men/products/jeans.html", "BOTTOM"),
        ("men-pants", f"{BASE_URL}/en_us/men/products/pants.html", "BOTTOM"),
        ("men-shoes", f"{BASE_URL}/en_us/men/products/shoes.html", "SHOE"),
        ("men-accessories", f"{BASE_URL}/en_us/men/products/accessories.html", "ACCESSORY"),
        # Women
        ("women-tops", f"{BASE_URL}/en_us/women/products/tops.html", "TOP"),
        ("women-shirts", f"{BASE_URL}/en_us/women/products/shirts-blouses.html", "TOP"),
        ("women-jeans", f"{BASE_URL}/en_us/women/products/jeans.html", "BOTTOM"),
        ("women-pants", f"{BASE_URL}/en_us/women/products/pants.html", "BOTTOM"),
        ("women-shoes", f"{BASE_URL}/en_us/women/products/shoes.html", "SHOE"),
        ("women-accessories", f"{BASE_URL}/en_us/women/products/accessories.html", "ACCESSORY"),
    ]

    async def scrape(self, max_products: int = 300) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        per_category = max(max_products // len(self.CATEGORY_URLS), 10)

        for label, url, cat_hint in self.CATEGORY_URLS:
            if len(products) >= max_products:
                break
            try:
                response = await self._fetch(url)
                if response is None:
                    logger.error(f"[H&M] Failed to fetch {label}")
                    continue

                page_products = self._parse_products(response, label, cat_hint)
                products.extend(page_products[:per_category])
                logger.info(f"[H&M] {label}: found {len(page_products)} products")
            except Exception as e:
                logger.error(f"[H&M] Failed to scrape {label}: {e}")

        logger.info(f"[H&M] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_products(self, response, label: str, cat_hint: str) -> list[ScrapedProduct]:
        """
        Extract products from an H&M listing page.
        Primary: JSON-LD structured data. Fallback: HTML product cards.

        H&M's JSON-LD uses ItemList > ListItem > item (Product) nesting,
        and AggregateOffer with lowPrice/highPrice instead of a flat price.
        """
        items: list[ScrapedProduct] = []

        # ── Primary: JSON-LD structured data ──
        jsonld_products = self._extract_hnm_jsonld(response)

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
                if not brand:
                    brand = "H&M"

                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                # H&M uses AggregateOffer with lowPrice / highPrice
                try:
                    price = float(
                        offers.get("lowPrice")
                        or offers.get("price")
                        or 0
                    )
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
                description = data.get("description", "") or f"H&M {name}"

                if name and price > 0 and product_url:
                    items.append(
                        ScrapedProduct(
                            name=self._clean_name(name),
                            price=round(price, 2),
                            product_url=product_url,
                            source="HNM",
                            brand=brand,
                            color=color,
                            description=description,
                            image_url=image_url,
                            category_hint=cat_hint,
                        )
                    )
            except (KeyError, TypeError) as e:
                logger.debug(f"[H&M] JSON-LD parse error: {e}")

        # ── Fallback: HTML product card scraping ──
        if not items:
            items = self._parse_html(response, cat_hint)

        return items

    def _extract_hnm_jsonld(self, response) -> list[dict]:
        """
        H&M-specific JSON-LD extraction.
        H&M wraps products in: ItemList > itemListElement[] > item (Product)
        Also handles direct Product entries via the base _parse_jsonld().
        """
        import json

        products: list[dict] = []

        # Try base class first (direct @type=Product)
        products.extend(self._parse_jsonld(response))

        # H&M-specific: ItemList nesting
        scripts = response.css('script[type="application/ld+json"]')
        for script in scripts:
            try:
                text = script.text
                if not text:
                    continue
                data = json.loads(text)

                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for entry in data.get("itemListElement", []):
                        item = entry.get("item", {})
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            products.append(item)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"[H&M] ItemList JSON-LD parse error: {e}")

        return products

    def _parse_html(self, response, cat_hint: str) -> list[ScrapedProduct]:
        """
        Fallback: parse H&M product listing HTML.
        H&M uses <article data-articlecode="XXXX"> cards with:
          - h2 for the product name
          - <span> / <del> for prices
          - <a href="/en_us/productpage.XXXX.html"> for links
          - <img> for product images
        """
        items: list[ScrapedProduct] = []

        # H&M product cards — article[data-articlecode] is the most reliable
        product_cards = response.css("[data-articlecode]")
        if not product_cards:
            product_cards = response.css("li.product-item")
        if not product_cards:
            product_cards = response.css("article")

        for card in product_cards:
            try:
                # ── Product name ──
                name_el = css_first(card, "h2, h3, .item-heading a, .product-item-headline")
                name = name_el.text.strip() if name_el else ""
                name = self._clean_name(name)
                if not name:
                    continue

                # ── Price ──
                # H&M shows sale price in <span> and strikethrough original in <del>
                price = 0.0

                # Try specific price selectors first
                for sel in ["span.price-value", ".sale", "p span"]:
                    price_el = css_first(card, sel)
                    if price_el and "$" in (price_el.text or ""):
                        price = self._parse_price(price_el.text)
                        if price > 0:
                            break

                # Broader fallback: scan all text for first dollar amount
                if price <= 0:
                    all_text = card.text or ""
                    price = self._parse_price(all_text)

                # ── URL ──
                link_el = css_first(card, "a[href*='productpage']")
                if not link_el:
                    link_el = css_first(card, "a[href]")
                raw_url = link_el.attrib.get("href", "") if link_el else ""
                if raw_url and not raw_url.startswith("http"):
                    product_url = f"{self.BASE_URL}{raw_url}"
                else:
                    product_url = raw_url

                # ── Image ──
                img_el = css_first(card, "img[src], img[data-src]")
                image_url = ""
                if img_el:
                    image_url = (
                        img_el.attrib.get("src", "")
                        or img_el.attrib.get("data-src", "")
                    )

                # ── Color ──
                color = self._extract_color(name)

                if name and price > 0 and product_url:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=round(price, 2),
                            product_url=product_url,
                            source="HNM",
                            brand="H&M",
                            color=color,
                            description=f"H&M {name}",
                            image_url=image_url,
                            category_hint=cat_hint,
                        )
                    )
            except Exception as e:
                logger.debug(f"[H&M] HTML parse error: {e}")

        return items

    # ── Helpers ──

    @staticmethod
    def _clean_name(name: str) -> str:
        """
        Clean H&M product name.
        H&M names often include color variants after a dash, e.g.
        'Regular Fit T-shirt - Black/White/Gray melange'
        We keep just the product name part before the color list.
        """
        if not name:
            return ""
        # Remove duplicate name (H&M renders it twice, e.g. "SLIM FIT T-SHIRT SLIM FIT T-SHIRT")
        words = name.split()
        half = len(words) // 2
        if half > 1 and words[:half] == words[half:2 * half]:
            name = " ".join(words[:half])

        # Take the part before " - " if the part after is color-like
        if " - " in name:
            parts = name.split(" - ", 1)
            # If the part after dash looks like colors (has /, or is a single color word)
            if "/" in parts[1] or len(parts[1].split()) <= 3:
                name = parts[0].strip()

        return name.strip()

    @staticmethod
    def _extract_color(name: str) -> str:
        """
        Extract color from H&M product name.
        H&M names follow the pattern: 'Product Name - Color/Color2/Color3'
        """
        colors = [
            "black", "white", "red", "blue", "green", "yellow", "pink",
            "purple", "orange", "brown", "gray", "grey", "navy", "beige",
            "cream", "olive", "maroon", "tan", "gold", "silver", "khaki",
            "burgundy", "charcoal", "taupe", "ivory", "coral", "teal",
            "indigo", "turquoise", "dark", "light", "sage",
        ]

        # Try to extract from the " - Color" suffix
        if " - " in name:
            color_part = name.split(" - ", 1)[1]
            # Take the first color variant (before /)
            first_variant = color_part.split("/")[0].strip()
            if first_variant:
                return first_variant.title()

        # Fallback: search name for known color words
        name_lower = name.lower()
        for color in colors:
            if f" {color} " in f" {name_lower} ":
                return color.capitalize()
        return ""

    @staticmethod
    def _parse_price(text: str) -> float:
        """Parse a price from text containing dollar amounts."""
        if not text:
            return 0.0
        # Find all dollar amounts; prefer the first (usually sale price)
        matches = re.findall(r"\$\s*([\d,]+\.?\d*)", text)
        if matches:
            try:
                return float(matches[0].replace(",", ""))
            except ValueError:
                pass
        return 0.0
