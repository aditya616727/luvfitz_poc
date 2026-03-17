"""
Product service – CRUD operations for products.
"""

from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.models import Product, CategoryEnum, SourceEnum
from app.schemas import ProductCreate, ProductUpdate
from app.core.logging import logger


class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: UUID) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_url(self, product_url: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.product_url == product_url).first()

    def get_all(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        available_only: bool = True,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Product], int]:
        query = self.db.query(Product)

        if available_only:
            query = query.filter(Product.availability == True)

        if category:
            query = query.filter(Product.category == CategoryEnum(category))

        if source:
            query = query.filter(Product.source == SourceEnum(source))

        if min_price is not None:
            query = query.filter(Product.price >= min_price)

        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        total = query.count()
        products = (
            query.order_by(Product.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return products, total

    def get_by_category(self, category: str, available_only: bool = True) -> list[Product]:
        query = self.db.query(Product).filter(Product.category == CategoryEnum(category))
        if available_only:
            query = query.filter(Product.availability == True)
        return query.all()

    def search(self, q: str, page: int = 1, per_page: int = 20) -> tuple[list[Product], int]:
        """Full-text search on product name and description."""
        query = self.db.query(Product).filter(
            and_(
                Product.availability == True,
                or_(
                    Product.name.ilike(f"%{q}%"),
                    Product.description.ilike(f"%{q}%"),
                    Product.brand.ilike(f"%{q}%"),
                ),
            )
        )

        total = query.count()
        products = (
            query.order_by(Product.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return products, total

    def upsert(self, data: dict) -> Product:
        """Insert or update a product based on product_url uniqueness."""
        existing = self.get_by_url(data["product_url"])

        if existing:
            for key, value in data.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            logger.debug(f"Updated product: {existing.name}")
            return existing
        else:
            product = Product(**data)
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            logger.debug(f"Created product: {product.name}")
            return product

    def update_price_and_availability(
        self, product_id: UUID, price: float, availability: bool
    ) -> Optional[Product]:
        product = self.get_by_id(product_id)
        if product:
            product.price = price
            product.availability = availability
            self.db.commit()
            self.db.refresh(product)
        return product

    def bulk_upsert(self, products_data: list[dict]) -> int:
        """Bulk upsert products. Returns count of successfully processed products."""
        count = 0
        for data in products_data:
            try:
                self.upsert(data)
                count += 1
            except Exception as e:
                logger.error(f"Failed to upsert product {data.get('name', '?')}: {e}")
                self.db.rollback()
        return count

    def count_by_category(self) -> dict[str, int]:
        results = (
            self.db.query(Product.category, func.count(Product.id))
            .filter(Product.availability == True)
            .group_by(Product.category)
            .all()
        )
        return {cat.value: count for cat, count in results}
