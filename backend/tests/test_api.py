"""
Tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app


client = TestClient(app)


class TestHealthEndpoints:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Mini Outfit Builder API"

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestProductEndpoints:
    @patch("app.api.products.ProductService")
    def test_list_products(self, MockService):
        mock_instance = MockService.return_value
        mock_instance.get_all.return_value = ([], 0)

        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @patch("app.api.products.ProductService")
    def test_search_products(self, MockService):
        mock_instance = MockService.return_value
        mock_instance.search.return_value = ([], 0)

        response = client.get("/api/products/search?q=shirt")
        assert response.status_code == 200

    def test_search_products_no_query(self):
        response = client.get("/api/products/search")
        assert response.status_code == 422  # validation error


class TestOutfitEndpoints:
    @patch("app.api.outfits.OutfitService")
    def test_list_outfits(self, MockService):
        mock_instance = MockService.return_value
        mock_instance.get_all.return_value = ([], 0)

        response = client.get("/api/outfits")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @patch("app.api.outfits.OutfitService")
    def test_search_outfits(self, MockService):
        mock_instance = MockService.return_value
        mock_instance.search_by_vibe.return_value = ([], 0)

        response = client.get("/api/outfits/search?q=casual")
        assert response.status_code == 200

    def test_search_outfits_no_query(self):
        response = client.get("/api/outfits/search")
        assert response.status_code == 422

    def test_get_outfit_not_found(self):
        response = client.get("/api/outfits/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
