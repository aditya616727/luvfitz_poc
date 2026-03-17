"""
Product API endpoints.
"""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.services.product_service import ProductService
from app.models.models import Product
from app.schemas import ProductResponse, PaginatedResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse)
def list_products(
    category: Optional[str] = Query(None, description="Filter by category: TOP, BOTTOM, SHOE, ACCESSORY"),
    source: Optional[str] = Query(None, description="Filter by source: ZAPPOS, AMAZON, SSENSE"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    products, total = service.get_all(
        category=category,
        source=source,
        min_price=min_price,
        max_price=max_price,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/search", response_model=PaginatedResponse)
def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = ProductService(db)
    products, total = service.search(q, page=page, per_page=per_page)
    return PaginatedResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/stats")
def product_stats(db: Session = Depends(get_db)):
    service = ProductService(db)
    return service.count_by_category()


@router.get("/taxonomy-stats")
def taxonomy_stats(db: Session = Depends(get_db)):
    """Return Google Product Taxonomy distribution across all products."""
    results = (
        db.query(
            Product.google_product_category,
            func.count(Product.id),
        )
        .filter(Product.availability == True)
        .group_by(Product.google_product_category)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    return {
        "total": sum(count for _, count in results),
        "categories": {cat or "Uncategorized": count for cat, count in results},
    }


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    service = ProductService(db)
    product = service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)
