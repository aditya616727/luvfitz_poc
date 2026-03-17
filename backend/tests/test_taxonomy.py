"""
Tests for taxonomy mapping utilities.
"""

import pytest
from app.utils.taxonomy import map_taxonomy, extract_style_tags


class TestMapTaxonomy:
    def test_shirt_maps_to_top(self):
        category, taxonomy = map_taxonomy("Classic Oxford Shirt")
        assert category == "TOP"
        assert "Shirts" in taxonomy

    def test_jeans_maps_to_bottom(self):
        category, taxonomy = map_taxonomy("Slim Fit Jeans")
        assert category == "BOTTOM"
        assert "Jeans" in taxonomy

    def test_sneakers_maps_to_shoe(self):
        category, taxonomy = map_taxonomy("Classic White Sneakers")
        assert category == "SHOE"
        assert "Athletic" in taxonomy or "Shoes" in taxonomy

    def test_bag_maps_to_accessory(self):
        category, taxonomy = map_taxonomy("Leather Crossbody Bag")
        assert category == "ACCESSORY"

    def test_unknown_product_returns_none(self):
        category, taxonomy = map_taxonomy("Mysterious Widget")
        assert category is None
        assert taxonomy is None

    def test_description_fallback(self):
        category, _ = map_taxonomy("Fashion Item", "A beautiful dress for evening wear")
        assert category == "TOP"  # "dress" maps to TOP

    def test_hoodie_maps_to_top(self):
        category, taxonomy = map_taxonomy("Oversized Hoodie")
        assert category == "TOP"
        assert "Hoodies" in taxonomy

    def test_shorts_maps_to_bottom(self):
        category, _ = map_taxonomy("Chino Shorts")
        assert category == "BOTTOM"

    def test_boots_maps_to_shoe(self):
        category, taxonomy = map_taxonomy("Chelsea Boots")
        assert category == "SHOE"
        assert "Boots" in taxonomy

    def test_watch_maps_to_accessory(self):
        category, _ = map_taxonomy("Minimalist Watch")
        assert category == "ACCESSORY"


class TestExtractStyleTags:
    def test_casual_tags(self):
        tags = extract_style_tags("Casual Cotton Shirt", "A comfortable relaxed fit shirt")
        assert "casual" in tags

    def test_formal_tags(self):
        tags = extract_style_tags("Formal Business Shirt", "Professional office wear")
        assert "formal" in tags

    def test_retro_tags(self):
        tags = extract_style_tags("Vintage Graphic Tee", "Retro 90s style print")
        assert "retro" in tags

    def test_date_night_tags(self):
        tags = extract_style_tags("Satin Camisole", "Romantic evening date look")
        assert "date-night" in tags

    def test_fallback_to_casual(self):
        tags = extract_style_tags("Plain Item", "No special description")
        assert "casual" in tags

    def test_color_based_tags(self):
        tags = extract_style_tags("Simple Top", "", "pastel pink")
        # Should have some tag
        assert len(tags) > 0

    def test_multiple_tags(self):
        tags = extract_style_tags("Casual Street Hoodie", "Urban streetwear comfortable style")
        assert len(tags) >= 2
