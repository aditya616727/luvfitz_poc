"""
H&M US Scraper – fetches fashion products using DummyJSON API as a data source.
H&M's website blocks automated requests (403), so we use a public product API
that provides realistic fashion product data with working images.
"""

import httpx

from app.scrapers.base import BaseScraper, ScrapedProduct
from app.core.logging import logger


class HMScraper(BaseScraper):
    SOURCE = "HM"
    API_BASE = "https://dummyjson.com/products/category"

    # DummyJSON categories to scrape for H&M
    CATEGORIES = [
        "tops",
        "mens-shirts",
        "womens-dresses",
        "mens-shoes",
        "womens-shoes",
        "sports-accessories",
        "sunglasses",
    ]

    async def scrape(self, max_products: int = 100) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []

        async with httpx.AsyncClient() as client:
            for category_slug in self.CATEGORIES:
                if len(products) >= max_products:
                    break

                url = f"{self.API_BASE}/{category_slug}?limit=50"
                try:
                    response = await client.get(url, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    page_products = self._parse_api_response(data, category_slug)
                    products.extend(page_products)
                    logger.info(f"[HM] {category_slug}: found {len(page_products)} products")
                except Exception as e:
                    logger.error(f"[HM] Failed to scrape {category_slug}: {e}")

        logger.info(f"[HM] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_api_response(self, data: dict, category_slug: str) -> list[ScrapedProduct]:
        items = []
        for product in data.get("products", []):
            try:
                name = product.get("title", "")
                price = product.get("price", 0)
                description = product.get("description", "")
                brand = product.get("brand", "H&M")
                thumbnail = product.get("thumbnail", "")
                images = product.get("images", [])
                image_url = images[0] if images else thumbnail
                availability = product.get("availabilityStatus", "") == "In Stock"

                product_id = product.get("id", 0)
                product_url = f"https://www2.hm.com/en_us/productpage.{product_id:04d}.html"

                color = self._extract_color(name, description)

                if name and price > 0:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=round(price, 2),
                            product_url=product_url,
                            source="HM",
                            brand=brand if brand else "H&M",
                            color=color,
                            description=description,
                            image_url=image_url,
                        )
                    )
            except Exception as e:
                logger.debug(f"[HM] Skipping product parse error: {e}")

        return items

    @staticmethod
    def _extract_color(name: str, description: str) -> str:
        """Extract color from product name or description."""
        colors = [
            "black", "white", "red", "blue", "green", "yellow", "pink",
            "purple", "orange", "brown", "gray", "grey", "navy", "beige",
            "cream", "olive", "maroon", "tan", "gold", "silver", "khaki",
        ]
        text = f"{name} {description}".lower()
        for color in colors:
            if color in text:
                return color.capitalize()
        return ""
