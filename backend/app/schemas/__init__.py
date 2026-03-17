"""
Pydantic schemas for API request/response serialization.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# ──────────────────────────────────────────────
# Product Schemas
# ──────────────────────────────────────────────
class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    price: float
    color: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    product_url: str
    category: str
    taxonomy: Optional[str] = None
    google_product_category: Optional[str] = None
    google_taxonomy_id: Optional[int] = None
    availability: bool = True
    source: str
    style_tags: list[str] = []


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    price: Optional[float] = None
    availability: Optional[bool] = None
    image_url: Optional[str] = None
    last_updated: Optional[datetime] = None


class ProductResponse(ProductBase):
    id: UUID
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Outfit Schemas
# ──────────────────────────────────────────────
class OutfitBase(BaseModel):
    style_tags: list[str] = []
    score: float = 0.0


class OutfitCreate(BaseModel):
    top_id: UUID
    bottom_id: UUID
    shoe_id: UUID
    accessory_id: UUID
    style_tags: list[str] = []
    score: float = 0.0


class OutfitResponse(OutfitBase):
    id: UUID
    top: ProductResponse
    bottom: ProductResponse
    shoe: ProductResponse
    accessory: ProductResponse
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Search / Pagination
# ──────────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    pages: int


class OutfitSearchParams(BaseModel):
    q: str = ""
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    page: int = 1
    per_page: int = 12


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    environment: str = "development"
