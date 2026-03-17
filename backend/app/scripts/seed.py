"""
Seed script – populates the database with sample products for development.
Run: python -m app.scripts.seed
"""

import random
from app.core.database import SessionLocal, engine, Base
from app.models.models import Product, CategoryEnum, SourceEnum
from app.services.product_service import ProductService
from app.services.outfit_service import OutfitService
from app.utils.taxonomy import extract_style_tags, map_taxonomy
from app.core.logging import logger

# ── Sample product data ──
# Using picsum.photos (reliable placeholder images)
# Sources: ZAPPOS, AMAZON, SSENSE (matching SourceEnum)
SAMPLE_PRODUCTS = [
    # TOPS
    {"name": "Classic Oxford Shirt", "brand": "Ralph Lauren", "price": 29.99, "color": "White", "description": "A timeless oxford button-down shirt in crisp white cotton", "image_url": "https://picsum.photos/seed/oxford-shirt/400/400", "product_url": "https://www.zappos.com/p/oxford-shirt-001", "source": "ZAPPOS"},
    {"name": "Vintage Graphic Tee", "brand": "Urban Outfitters", "price": 35.00, "color": "Black", "description": "Retro 90s graphic print t-shirt with oversized fit", "image_url": "https://picsum.photos/seed/graphic-tee/400/400", "product_url": "https://www.amazon.com/dp/B001", "source": "AMAZON"},
    {"name": "Silk Blouse", "brand": "Vince", "price": 89.00, "color": "Navy", "description": "Elegant silk blouse perfect for date night or office wear", "image_url": "https://picsum.photos/seed/silk-blouse/400/400", "product_url": "https://www.ssense.com/en-us/women/product/silk-blouse/001", "source": "SSENSE"},
    {"name": "Oversized Hoodie", "brand": "Champion", "price": 34.99, "color": "Gray", "description": "Comfortable oversized hoodie in soft fleece for streetwear looks", "image_url": "https://picsum.photos/seed/hoodie/400/400", "product_url": "https://www.zappos.com/p/hoodie-002", "source": "ZAPPOS"},
    {"name": "Linen Summer Top", "brand": "J.Crew", "price": 24.99, "color": "Beige", "description": "Lightweight linen top for breezy summer days", "image_url": "https://picsum.photos/seed/linen-top/400/400", "product_url": "https://www.zappos.com/p/linen-top-003", "source": "ZAPPOS"},
    {"name": "Cashmere Sweater", "brand": "Theory", "price": 149.00, "color": "Cream", "description": "Luxurious cashmere sweater with a minimalist clean silhouette", "image_url": "https://picsum.photos/seed/cashmere/400/400", "product_url": "https://www.ssense.com/en-us/women/product/cashmere-sweater/002", "source": "SSENSE"},
    {"name": "Flannel Plaid Shirt", "brand": "Amazon Essentials", "price": 22.00, "color": "Red", "description": "Classic plaid flannel shirt with a casual relaxed fit", "image_url": "https://picsum.photos/seed/flannel/400/400", "product_url": "https://www.amazon.com/dp/B002", "source": "AMAZON"},
    {"name": "Cropped Tank Top", "brand": "Calvin Klein", "price": 12.99, "color": "Pink", "description": "Sporty cropped tank top in pastel pink", "image_url": "https://picsum.photos/seed/tank-top/400/400", "product_url": "https://www.zappos.com/p/tank-top-004", "source": "ZAPPOS"},
    {"name": "Denim Jacket", "brand": "Levi's", "price": 79.50, "color": "Blue", "description": "Iconic denim trucker jacket perfect for casual streetwear", "image_url": "https://picsum.photos/seed/denim-jacket/400/400", "product_url": "https://www.amazon.com/dp/B003", "source": "AMAZON"},
    {"name": "Satin Camisole", "brand": "Saint Laurent", "price": 55.00, "color": "Black", "description": "Sleek satin camisole for a romantic date night look", "image_url": "https://picsum.photos/seed/satin-cami/400/400", "product_url": "https://www.ssense.com/en-us/women/product/satin-cami/003", "source": "SSENSE"},

    # BOTTOMS
    {"name": "Slim Fit Jeans", "brand": "Levi's", "price": 69.50, "color": "Indigo", "description": "Classic slim fit jeans in dark indigo wash", "image_url": "https://picsum.photos/seed/slim-jeans/400/400", "product_url": "https://www.amazon.com/dp/B004", "source": "AMAZON"},
    {"name": "High-Waist Trousers", "brand": "Theory", "price": 39.99, "color": "Black", "description": "Elegant high-waist trousers for a formal professional look", "image_url": "https://picsum.photos/seed/trousers/400/400", "product_url": "https://www.ssense.com/en-us/women/product/trousers/004", "source": "SSENSE"},
    {"name": "Cargo Joggers", "brand": "Nike", "price": 29.99, "color": "Olive", "description": "Relaxed cargo joggers for a streetwear urban style", "image_url": "https://picsum.photos/seed/cargo-joggers/400/400", "product_url": "https://www.zappos.com/p/cargo-joggers-005", "source": "ZAPPOS"},
    {"name": "Pleated Midi Skirt", "brand": "Acne Studios", "price": 75.00, "color": "Blush", "description": "Flowing pleated midi skirt in pastel blush", "image_url": "https://picsum.photos/seed/midi-skirt/400/400", "product_url": "https://www.ssense.com/en-us/women/product/midi-skirt/005", "source": "SSENSE"},
    {"name": "Chino Shorts", "brand": "Amazon Essentials", "price": 20.00, "color": "Khaki", "description": "Classic chino shorts for a casual summer look", "image_url": "https://picsum.photos/seed/chino-shorts/400/400", "product_url": "https://www.amazon.com/dp/B005", "source": "AMAZON"},
    {"name": "Wide-Leg Pants", "brand": "Free People", "price": 34.99, "color": "Cream", "description": "Flowy wide-leg pants with a bohemian earthy feel", "image_url": "https://picsum.photos/seed/wide-leg/400/400", "product_url": "https://www.zappos.com/p/wide-leg-006", "source": "ZAPPOS"},
    {"name": "Athletic Leggings", "brand": "Nike", "price": 55.00, "color": "Black", "description": "High-performance athletic leggings for gym and sport", "image_url": "https://picsum.photos/seed/leggings/400/400", "product_url": "https://www.amazon.com/dp/B006", "source": "AMAZON"},
    {"name": "Corduroy Pants", "brand": "AMI Paris", "price": 68.00, "color": "Brown", "description": "Retro-inspired corduroy pants with vintage 70s charm", "image_url": "https://picsum.photos/seed/corduroy/400/400", "product_url": "https://www.ssense.com/en-us/men/product/corduroy-pants/006", "source": "SSENSE"},
    {"name": "Denim Cutoff Shorts", "brand": "Levi's", "price": 19.99, "color": "Light Blue", "description": "Relaxed denim cutoff shorts for summer beach vibes", "image_url": "https://picsum.photos/seed/cutoff-shorts/400/400", "product_url": "https://www.zappos.com/p/cutoff-shorts-007", "source": "ZAPPOS"},
    {"name": "Tailored Wool Pants", "brand": "Jil Sander", "price": 120.00, "color": "Charcoal", "description": "Tailored wool pants for a sophisticated formal look", "image_url": "https://picsum.photos/seed/wool-pants/400/400", "product_url": "https://www.ssense.com/en-us/men/product/wool-pants/007", "source": "SSENSE"},

    # SHOES
    {"name": "Classic White Sneakers", "brand": "Adidas", "price": 85.00, "color": "White", "description": "Clean white leather sneakers for everyday casual wear", "image_url": "https://picsum.photos/seed/white-sneakers/400/400", "product_url": "https://www.amazon.com/dp/B007", "source": "AMAZON"},
    {"name": "Chelsea Boots", "brand": "Dr. Martens", "price": 150.00, "color": "Black", "description": "Sleek black leather chelsea boots for formal and date-night looks", "image_url": "https://picsum.photos/seed/chelsea-boots/400/400", "product_url": "https://www.zappos.com/p/chelsea-boots-008", "source": "ZAPPOS"},
    {"name": "Running Shoes", "brand": "Nike", "price": 120.00, "color": "Black", "description": "High-performance running shoes for athletic training", "image_url": "https://picsum.photos/seed/running-shoes/400/400", "product_url": "https://www.amazon.com/dp/B008", "source": "AMAZON"},
    {"name": "Strappy Sandals", "brand": "Steve Madden", "price": 24.99, "color": "Tan", "description": "Minimalist strappy sandals for summer beach days", "image_url": "https://picsum.photos/seed/sandals/400/400", "product_url": "https://www.zappos.com/p/sandals-009", "source": "ZAPPOS"},
    {"name": "Suede Loafers", "brand": "Gucci", "price": 95.00, "color": "Brown", "description": "Classic suede loafers with a timeless elegant finish", "image_url": "https://picsum.photos/seed/loafers/400/400", "product_url": "https://www.ssense.com/en-us/men/product/suede-loafers/008", "source": "SSENSE"},
    {"name": "Platform Sneakers", "brand": "Converse", "price": 75.00, "color": "Black", "description": "Retro platform sneakers with a 90s throwback vibe", "image_url": "https://picsum.photos/seed/platform-sneakers/400/400", "product_url": "https://www.amazon.com/dp/B009", "source": "AMAZON"},
    {"name": "Block Heel Pumps", "brand": "Stuart Weitzman", "price": 110.00, "color": "Red", "description": "Statement block heel pumps for a romantic evening out", "image_url": "https://picsum.photos/seed/block-heels/400/400", "product_url": "https://www.ssense.com/en-us/women/product/block-heels/009", "source": "SSENSE"},
    {"name": "Canvas Slip-Ons", "brand": "Vans", "price": 50.00, "color": "Navy", "description": "Classic canvas slip-on shoes for casual everyday wear", "image_url": "https://picsum.photos/seed/slip-ons/400/400", "product_url": "https://www.amazon.com/dp/B010", "source": "AMAZON"},
    {"name": "Ankle Boots", "brand": "Clarks", "price": 49.99, "color": "Black", "description": "Versatile ankle boots with a bohemian western flair", "image_url": "https://picsum.photos/seed/ankle-boots/400/400", "product_url": "https://www.zappos.com/p/ankle-boots-010", "source": "ZAPPOS"},
    {"name": "Espadrille Wedges", "brand": "Castaner", "price": 85.00, "color": "Tan", "description": "Summer espadrille wedge sandals with tropical vibes", "image_url": "https://picsum.photos/seed/espadrilles/400/400", "product_url": "https://www.ssense.com/en-us/women/product/espadrilles/010", "source": "SSENSE"},

    # ACCESSORIES
    {"name": "Leather Crossbody Bag", "brand": "Coach", "price": 29.99, "color": "Brown", "description": "Compact leather crossbody bag for everyday casual use", "image_url": "https://picsum.photos/seed/crossbody-bag/400/400", "product_url": "https://www.zappos.com/p/crossbody-bag-011", "source": "ZAPPOS"},
    {"name": "Aviator Sunglasses", "brand": "Ray-Ban", "price": 163.00, "color": "Gold", "description": "Iconic aviator sunglasses with a retro vintage look", "image_url": "https://picsum.photos/seed/aviator-sunglasses/400/400", "product_url": "https://www.ssense.com/en-us/men/product/aviator-sunglasses/011", "source": "SSENSE"},
    {"name": "Canvas Tote Bag", "brand": "Amazon Essentials", "price": 18.00, "color": "Natural", "description": "Simple canvas tote bag for casual summer outings", "image_url": "https://picsum.photos/seed/canvas-tote/400/400", "product_url": "https://www.amazon.com/dp/B011", "source": "AMAZON"},
    {"name": "Gold Chain Necklace", "brand": "Mejuri", "price": 45.00, "color": "Gold", "description": "Delicate gold chain necklace for a minimalist elegant touch", "image_url": "https://picsum.photos/seed/gold-necklace/400/400", "product_url": "https://www.ssense.com/en-us/women/product/gold-necklace/012", "source": "SSENSE"},
    {"name": "Baseball Cap", "brand": "Nike", "price": 28.00, "color": "Black", "description": "Classic baseball cap for sporty streetwear looks", "image_url": "https://picsum.photos/seed/baseball-cap/400/400", "product_url": "https://www.amazon.com/dp/B012", "source": "AMAZON"},
    {"name": "Leather Belt", "brand": "Fossil", "price": 19.99, "color": "Black", "description": "Classic leather belt with minimalist silver buckle", "image_url": "https://picsum.photos/seed/leather-belt/400/400", "product_url": "https://www.zappos.com/p/leather-belt-012", "source": "ZAPPOS"},
    {"name": "Wool Scarf", "brand": "Acne Studios", "price": 58.00, "color": "Burgundy", "description": "Soft wool scarf in rich burgundy for cozy winter layering", "image_url": "https://picsum.photos/seed/wool-scarf/400/400", "product_url": "https://www.ssense.com/en-us/men/product/wool-scarf/013", "source": "SSENSE"},
    {"name": "Straw Beach Hat", "brand": "Billabong", "price": 14.99, "color": "Natural", "description": "Wide-brim straw hat for tropical summer beach days", "image_url": "https://picsum.photos/seed/straw-hat/400/400", "product_url": "https://www.zappos.com/p/straw-hat-013", "source": "ZAPPOS"},
    {"name": "Minimalist Watch", "brand": "Daniel Wellington", "price": 179.00, "color": "Silver", "description": "Clean minimalist watch with leather strap for formal occasions", "image_url": "https://picsum.photos/seed/minimalist-watch/400/400", "product_url": "https://www.amazon.com/dp/B013", "source": "AMAZON"},
    {"name": "Bohemian Earrings", "brand": "Isabel Marant", "price": 32.00, "color": "Gold", "description": "Statement bohemian dangle earrings with natural stone accents", "image_url": "https://picsum.photos/seed/boho-earrings/400/400", "product_url": "https://www.ssense.com/en-us/women/product/boho-earrings/014", "source": "SSENSE"},
]


def seed_database():
    """Seed the database with sample products and generate outfits."""
    logger.info("Starting database seed...")

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        product_service = ProductService(db)

        # Seed products
        count = 0
        for product_data in SAMPLE_PRODUCTS:
            # Apply taxonomy mapping
            category, taxonomy = map_taxonomy(product_data["name"], product_data.get("description", ""))
            style_tags = extract_style_tags(
                product_data["name"],
                product_data.get("description", ""),
                product_data.get("color", ""),
            )

            if category is None:
                logger.warning(f"Skipping unmappable product: {product_data['name']}")
                continue

            full_data = {
                **product_data,
                "category": category,
                "taxonomy": taxonomy,
                "style_tags": style_tags,
                "availability": True,
            }

            try:
                product_service.upsert(full_data)
                count += 1
            except Exception as e:
                logger.error(f"Failed to seed: {product_data['name']}: {e}")
                db.rollback()

        logger.info(f"Seeded {count} products")

        # Generate outfits
        outfit_service = OutfitService(db)
        generated = outfit_service.generate_outfits(max_outfits=50)
        logger.info(f"Generated {generated} outfits")

        # Print stats
        stats = product_service.count_by_category()
        logger.info(f"Product stats: {stats}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
