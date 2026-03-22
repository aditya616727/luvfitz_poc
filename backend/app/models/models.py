"""
SQLAlchemy ORM models – Products & Outfits.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    Integer,
    Text,
    Enum as SAEnum,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────
class CategoryEnum(str, enum.Enum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    SHOE = "SHOE"
    ACCESSORY = "ACCESSORY"


class SourceEnum(str, enum.Enum):
    ZAPPOS = "ZAPPOS"
    AMAZON = "AMAZON"
    SSENSE = "SSENSE"
    HNM = "HNM"


# ──────────────────────────────────────────────
# Product
# ──────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, index=True)
    brand = Column(String(255), nullable=True)
    price = Column(Float, nullable=False)
    color = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    product_url = Column(Text, nullable=False, unique=True)
    category = Column(SAEnum(CategoryEnum, name="category_enum"), nullable=False, index=True)
    taxonomy = Column(Text, nullable=True)
    google_product_category = Column(Text, nullable=True, index=True)
    google_taxonomy_id = Column(Integer, nullable=True)
    availability = Column(Boolean, default=True, index=True)
    source = Column(SAEnum(SourceEnum, name="source_enum"), nullable=False, index=True)
    style_tags = Column(ARRAY(String), default=list)
    last_updated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_products_category_availability", "category", "availability"),
        Index("ix_products_source_category", "source", "category"),
    )

    def __repr__(self) -> str:
        return f"<Product {self.name} ({self.category.value}) ${self.price}>"


# ──────────────────────────────────────────────
# Outfit
# ──────────────────────────────────────────────
class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    top_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    bottom_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    shoe_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    accessory_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    style_tags = Column(ARRAY(String), default=list)
    score = Column(Float, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    top = relationship("Product", foreign_keys=[top_id], lazy="joined")
    bottom = relationship("Product", foreign_keys=[bottom_id], lazy="joined")
    shoe = relationship("Product", foreign_keys=[shoe_id], lazy="joined")
    accessory = relationship("Product", foreign_keys=[accessory_id], lazy="joined")

    __table_args__ = (
        Index("ix_outfits_style_tags", "style_tags", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Outfit {self.id} score={self.score}>"
