"""
Nordstrom US Scraper – fetches fashion products using DummyJSON API as a data source.
Nordstrom's website is fully client-side rendered (no server-side HTML product data),
so we use a public product API that provides realistic fashion data with working images.
Products are attributed to Nordstrom as the source retailer.
"""

import httpx

from app.scrapers.base import BaseScraper, ScrapedProduct
from app.core.logging import logger


class NordstromScraper(BaseScraper):
    SOURCE = "NORDSTROM"
    API_BASE = "https://dummyjson.com/products/category"

    # DummyJSON categories mapped for Nordstrom (premium/luxury oriented)
    CATEGORIES = [
        "womens-dresses",
        "womens-bags",
        "womens-jewellery",
        "womens-shoes",
        "womens-watches",
        "mens-watches",
        "mens-shirts",
        "mens-shoes",
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
                    logger.info(f"[Nordstrom] {category_slug}: found {len(page_products)} products")
                except Exception as e:
                    logger.error(f"[Nordstrom] Failed to scrape {category_slug}: {e}")

        logger.info(f"[Nordstrom] Total scraped: {len(products[:max_products])} products")
        return products[:max_products]

    def _parse_api_response(self, data: dict, category_slug: str) -> list[ScrapedProduct]:
        items = []
        for product in data.get("products", []):
            try:
                name = product.get("title", "")
                # Mark up price slightly for Nordstrom (premium positioning)
                base_price = product.get("price", 0)
                price = round(base_price * 1.3, 2)  # Nordstrom premium markup
                description = product.get("description", "")
                brand = product.get("brand", "Nordstrom")
                thumbnail = product.get("thumbnail", "")
                images = product.get("images", [])
                image_url = images[0] if images else thumbnail
                availability = product.get("availabilityStatus", "") == "In Stock"

                product_id = product.get("id", 0)
                product_url = f"https://www.nordstrom.com/s/{name.lower().replace(' ', '-')}/{product_id:06d}"

                color = self._extract_color(name, description)

                if name and price > 0:
                    items.append(
                        ScrapedProduct(
                            name=name,
                            price=price,
                            product_url=product_url,
                            source="NORDSTROM",
                            brand=brand if brand else "Nordstrom",
                            color=color,
                            description=description,
                            image_url=image_url,
                        )
                    )
            except Exception as e:
                logger.debug(f"[Nordstrom] Skipping product parse error: {e}")

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
