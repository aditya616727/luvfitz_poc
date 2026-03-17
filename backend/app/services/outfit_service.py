"""
Outfit builder engine – generates and scores outfit combinations.
"""

import random
import itertools
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.models import Product, Outfit, CategoryEnum
from app.services.product_service import ProductService
from app.utils.colors import color_harmony_score
from app.core.logging import logger


# ──────────────────────────────────────────────
# Style compatibility rules
# ──────────────────────────────────────────────
STYLE_COMPATIBILITY = {
    "casual": {"casual", "streetwear", "summer", "sporty", "minimalist"},
    "formal": {"formal", "minimalist", "date-night"},
    "streetwear": {"streetwear", "casual", "retro", "sporty"},
    "date-night": {"date-night", "formal", "minimalist", "boho"},
    "retro": {"retro", "streetwear", "casual", "boho"},
    "summer": {"summer", "casual", "boho"},
    "winter": {"winter", "casual", "minimalist"},
    "sporty": {"sporty", "casual", "streetwear"},
    "boho": {"boho", "summer", "retro", "casual"},
    "minimalist": {"minimalist", "casual", "formal", "date-night"},
}


class OutfitService:
    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)

    # ──────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────
    def get_by_id(self, outfit_id: UUID) -> Optional[Outfit]:
        return self.db.query(Outfit).filter(Outfit.id == outfit_id).first()

    def get_all(self, page: int = 1, per_page: int = 12) -> tuple[list[Outfit], int]:
        query = self.db.query(Outfit).order_by(Outfit.score.desc())
        total = query.count()
        outfits = query.offset((page - 1) * per_page).limit(per_page).all()
        return outfits, total

    def search_by_vibe(
        self,
        vibe: str,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        page: int = 1,
        per_page: int = 12,
    ) -> tuple[list[Outfit], int]:
        """Search outfits by vibe/style tag."""
        vibe_normalized = vibe.lower().strip().replace(" ", "-")

        query = self.db.query(Outfit).filter(
            Outfit.style_tags.any(vibe_normalized)
        )

        # Price filtering via joined products
        if min_price is not None or max_price is not None:
            query = query.join(Product, Outfit.top_id == Product.id)
            if min_price is not None:
                query = query.filter(Product.price >= min_price)
            if max_price is not None:
                query = query.filter(Product.price <= max_price)

        query = query.order_by(Outfit.score.desc())
        total = query.count()
        outfits = query.offset((page - 1) * per_page).limit(per_page).all()
        return outfits, total

    # ──────────────────────────────────────────
    # GENERATE
    # ──────────────────────────────────────────
    def generate_outfits(self, max_outfits: int = 50) -> int:
        """
        Generate outfit combinations from available products.
        Uses style-aware matching and scoring.
        """
        tops = self.product_service.get_by_category("TOP")
        bottoms = self.product_service.get_by_category("BOTTOM")
        shoes = self.product_service.get_by_category("SHOE")
        accessories = self.product_service.get_by_category("ACCESSORY")

        if not all([tops, bottoms, shoes, accessories]):
            logger.warning("Not enough products in all categories to generate outfits")
            return 0

        logger.info(
            f"Generating outfits from: {len(tops)} tops, {len(bottoms)} bottoms, "
            f"{len(shoes)} shoes, {len(accessories)} accessories"
        )

        generated = 0
        attempts = 0
        max_attempts = max_outfits * 5  # avoid infinite loops

        # Shuffle for variety
        random.shuffle(tops)
        random.shuffle(bottoms)
        random.shuffle(shoes)
        random.shuffle(accessories)

        seen_combos: set[tuple] = set()

        while generated < max_outfits and attempts < max_attempts:
            attempts += 1

            top = random.choice(tops)
            bottom = random.choice(bottoms)
            shoe = random.choice(shoes)
            accessory = random.choice(accessories)

            combo_key = (str(top.id), str(bottom.id), str(shoe.id), str(accessory.id))
            if combo_key in seen_combos:
                continue
            seen_combos.add(combo_key)

            # Check style compatibility
            if not self._are_style_compatible(top, bottom, shoe, accessory):
                continue

            # Score the outfit
            score = self._score_outfit(top, bottom, shoe, accessory)

            # Determine outfit style tags
            style_tags = self._compute_outfit_tags(top, bottom, shoe, accessory)

            # Check for existing outfit
            existing = (
                self.db.query(Outfit)
                .filter(
                    and_(
                        Outfit.top_id == top.id,
                        Outfit.bottom_id == bottom.id,
                        Outfit.shoe_id == shoe.id,
                        Outfit.accessory_id == accessory.id,
                    )
                )
                .first()
            )

            if existing:
                continue

            outfit = Outfit(
                top_id=top.id,
                bottom_id=bottom.id,
                shoe_id=shoe.id,
                accessory_id=accessory.id,
                style_tags=style_tags,
                score=score,
            )
            self.db.add(outfit)
            generated += 1

        self.db.commit()
        logger.info(f"Generated {generated} outfits in {attempts} attempts")
        return generated

    def _are_style_compatible(self, *products: Product) -> bool:
        """Check if products share compatible styles."""
        all_tags = [set(p.style_tags or []) for p in products]

        if not any(all_tags):
            return True  # No tags = allow

        # At least one common style across top & bottom
        for i in range(len(all_tags)):
            for j in range(i + 1, len(all_tags)):
                tags_i = all_tags[i]
                tags_j = all_tags[j]
                if tags_i and tags_j:
                    # Check direct overlap
                    if tags_i & tags_j:
                        continue
                    # Check compatibility map
                    compatible = False
                    for tag_i in tags_i:
                        compat_set = STYLE_COMPATIBILITY.get(tag_i, set())
                        if tags_j & compat_set:
                            compatible = True
                            break
                    if not compatible:
                        return False
        return True

    def _score_outfit(self, top: Product, bottom: Product, shoe: Product, accessory: Product) -> float:
        """Score an outfit from 0 to 1 based on multiple factors."""
        scores = []

        # 1. Color harmony (40% weight)
        colors = [p.color for p in [top, bottom, shoe, accessory] if p.color]
        if colors:
            scores.append(("color", color_harmony_score(colors), 0.4))
        else:
            scores.append(("color", 0.7, 0.4))  # neutral score when no color data

        # 2. Price similarity (20% weight) – more similar prices = better
        prices = [top.price, bottom.price, shoe.price, accessory.price]
        avg_price = sum(prices) / len(prices)
        price_variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        # Normalize: low variance = high score
        price_score = max(0, 1.0 - (price_variance / (avg_price ** 2 + 1)))
        scores.append(("price", price_score, 0.2))

        # 3. Style coherence (30% weight)
        all_tags = []
        for p in [top, bottom, shoe, accessory]:
            all_tags.extend(p.style_tags or [])
        if all_tags:
            from collections import Counter
            tag_counts = Counter(all_tags)
            most_common_count = tag_counts.most_common(1)[0][1]
            style_score = most_common_count / len([top, bottom, shoe, accessory])
        else:
            style_score = 0.5
        scores.append(("style", style_score, 0.3))

        # 4. Brand diversity bonus (10% weight) – mix of brands is interesting
        brands = set(p.brand for p in [top, bottom, shoe, accessory] if p.brand)
        brand_score = min(1.0, len(brands) / 3)
        scores.append(("brand", brand_score, 0.1))

        # Weighted average
        total_score = sum(score * weight for _, score, weight in scores)
        return round(min(1.0, max(0.0, total_score)), 3)

    def _compute_outfit_tags(self, *products: Product) -> list[str]:
        """Compute the combined style tags for an outfit."""
        from collections import Counter
        all_tags: list[str] = []
        for p in products:
            all_tags.extend(p.style_tags or [])

        if not all_tags:
            return ["casual"]

        # Return tags that appear in at least 2 products, or all unique if none repeat
        counter = Counter(all_tags)
        common = [tag for tag, count in counter.items() if count >= 2]
        return common if common else list(set(all_tags))

    def delete_all(self) -> int:
        """Delete all outfits (useful before regeneration)."""
        count = self.db.query(Outfit).delete()
        self.db.commit()
        return count
