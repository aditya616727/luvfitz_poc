"""
Tests for scraper base class and normalization.
"""

import pytest
from app.scrapers.base import ScrapedProduct


class TestScrapedProduct:
    def test_normalize_shirt(self):
        product = ScrapedProduct(
            name="Classic Oxford Shirt",
            price=29.99,
            product_url="https://example.com/shirt",
            source="ZAPPOS",
            brand="Ralph Lauren",
            color="White",
            description="A classic button-down shirt",
        )
        product.normalize()

        assert product.category == "TOP"
        assert product.taxonomy is not None
        assert "Shirts" in product.taxonomy
        assert len(product.style_tags) > 0

    def test_normalize_jeans(self):
        product = ScrapedProduct(
            name="Slim Fit Jeans",
            price=49.99,
            product_url="https://example.com/jeans",
            source="AMAZON",
            color="Blue",
        )
        product.normalize()

        assert product.category == "BOTTOM"
        assert "Jeans" in product.taxonomy

    def test_normalize_unknown(self):
        product = ScrapedProduct(
            name="Unknown Item",
            price=10.00,
            product_url="https://example.com/unknown",
            source="SSENSE",
        )
        product.normalize()

        assert product.category is None

    def test_to_dict(self):
        product = ScrapedProduct(
            name="Test Shirt",
            price=25.00,
            product_url="https://example.com/test",
            source="ZAPPOS",
        )
        product.normalize()
        d = product.to_dict()

        assert isinstance(d, dict)
        assert d["name"] == "Test Shirt"
        assert d["price"] == 25.00
        assert d["source"] == "ZAPPOS"
        assert "category" in d
        assert "style_tags" in d

    def test_availability_default(self):
        product = ScrapedProduct(
            name="Sneaker",
            price=100.00,
            product_url="https://example.com/sneaker",
            source="AMAZON",
        )
        assert product.availability is True
