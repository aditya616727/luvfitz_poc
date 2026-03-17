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
# Using picsum.photos (reliable placeholder) and fakestoreapi images
SAMPLE_PRODUCTS = [
    # TOPS
    {"name": "Classic Oxford Shirt", "brand": "H&M", "price": 29.99, "color": "White", "description": "A timeless oxford button-down shirt in crisp white cotton", "image_url": "https://picsum.photos/seed/oxford-shirt/400/400", "product_url": "https://www2.hm.com/en_us/productpage.001.html", "source": "HM"},
    {"name": "Vintage Graphic Tee", "brand": "Urban Outfitters", "price": 35.00, "color": "Black", "description": "Retro 90s graphic print t-shirt with oversized fit", "image_url": "https://picsum.photos/seed/graphic-tee/400/400", "product_url": "https://www.amazon.com/dp/B001", "source": "AMAZON"},
    {"name": "Silk Blouse", "brand": "Nordstrom", "price": 89.00, "color": "Navy", "description": "Elegant silk blouse perfect for date night or office wear", "image_url": "https://picsum.photos/seed/silk-blouse/400/400", "product_url": "https://www.nordstrom.com/s/silk-blouse/001", "source": "NORDSTROM"},
    {"name": "Oversized Hoodie", "brand": "H&M", "price": 34.99, "color": "Gray", "description": "Comfortable oversized hoodie in soft fleece for streetwear looks", "image_url": "https://picsum.photos/seed/hoodie/400/400", "product_url": "https://www2.hm.com/en_us/productpage.002.html", "source": "HM"},
    {"name": "Linen Summer Top", "brand": "H&M", "price": 24.99, "color": "Beige", "description": "Lightweight linen top for breezy summer days", "image_url": "https://picsum.photos/seed/linen-top/400/400", "product_url": "https://www2.hm.com/en_us/productpage.003.html", "source": "HM"},
    {"name": "Cashmere Sweater", "brand": "Nordstrom", "price": 149.00, "color": "Cream", "description": "Luxurious cashmere sweater with a minimalist clean silhouette", "image_url": "https://picsum.photos/seed/cashmere/400/400", "product_url": "https://www.nordstrom.com/s/cashmere-sweater/002", "source": "NORDSTROM"},
    {"name": "Flannel Plaid Shirt", "brand": "Amazon Essentials", "price": 22.00, "color": "Red", "description": "Classic plaid flannel shirt with a casual relaxed fit", "image_url": "https://picsum.photos/seed/flannel/400/400", "product_url": "https://www.amazon.com/dp/B002", "source": "AMAZON"},
    {"name": "Cropped Tank Top", "brand": "H&M", "price": 12.99, "color": "Pink", "description": "Sporty cropped tank top in pastel pink", "image_url": "https://picsum.photos/seed/tank-top/400/400", "product_url": "https://www2.hm.com/en_us/productpage.004.html", "source": "HM"},
    {"name": "Denim Jacket", "brand": "Levi's", "price": 79.50, "color": "Blue", "description": "Iconic denim trucker jacket perfect for casual streetwear", "image_url": "https://picsum.photos/seed/denim-jacket/400/400", "product_url": "https://www.amazon.com/dp/B003", "source": "AMAZON"},
    {"name": "Satin Camisole", "brand": "Nordstrom", "price": 55.00, "color": "Black", "description": "Sleek satin camisole for a romantic date night look", "image_url": "https://picsum.photos/seed/satin-cami/400/400", "product_url": "https://www.nordstrom.com/s/satin-cami/003", "source": "NORDSTROM"},

    # BOTTOMS
    {"name": "Slim Fit Jeans", "brand": "Levi's", "price": 69.50, "color": "Indigo", "description": "Classic slim fit jeans in dark indigo wash", "image_url": "https://picsum.photos/seed/slim-jeans/400/400", "product_url": "https://www.amazon.com/dp/B004", "source": "AMAZON"},
    {"name": "High-Waist Trousers", "brand": "H&M", "price": 39.99, "color": "Black", "description": "Elegant high-waist trousers for a formal professional look", "image_url": "https://picsum.photos/seed/trousers/400/400", "product_url": "https://www2.hm.com/en_us/productpage.005.html", "source": "HM"},
    {"name": "Cargo Joggers", "brand": "H&M", "price": 29.99, "color": "Olive", "description": "Relaxed cargo joggers for a streetwear urban style", "image_url": "https://picsum.photos/seed/cargo-joggers/400/400", "product_url": "https://www2.hm.com/en_us/productpage.006.html", "source": "HM"},
    {"name": "Pleated Midi Skirt", "brand": "Nordstrom", "price": 75.00, "color": "Blush", "description": "Flowing pleated midi skirt in pastel blush", "image_url": "https://picsum.photos/seed/midi-skirt/400/400", "product_url": "https://www.nordstrom.com/s/pleated-skirt/004", "source": "NORDSTROM"},
    {"name": "Chino Shorts", "brand": "Amazon Essentials", "price": 20.00, "color": "Khaki", "description": "Classic chino shorts for a casual summer look", "image_url": "https://picsum.photos/seed/chino-shorts/400/400", "product_url": "https://www.amazon.com/dp/B005", "source": "AMAZON"},
    {"name": "Wide-Leg Pants", "brand": "H&M", "price": 34.99, "color": "Cream", "description": "Flowy wide-leg pants with a bohemian earthy feel", "image_url": "https://picsum.photos/seed/wide-leg/400/400", "product_url": "https://www2.hm.com/en_us/productpage.007.html", "source": "HM"},
    {"name": "Athletic Leggings", "brand": "Nike", "price": 55.00, "color": "Black", "description": "High-performance athletic leggings for gym and sport", "image_url": "https://picsum.photos/seed/leggings/400/400", "product_url": "https://www.amazon.com/dp/B006", "source": "AMAZON"},
    {"name": "Corduroy Pants", "brand": "Nordstrom", "price": 68.00, "color": "Brown", "description": "Retro-inspired corduroy pants with vintage 70s charm", "image_url": "https://picsum.photos/seed/corduroy/400/400", "product_url": "https://www.nordstrom.com/s/corduroy-pants/005", "source": "NORDSTROM"},
    {"name": "Denim Cutoff Shorts", "brand": "H&M", "price": 19.99, "color": "Light Blue", "description": "Relaxed denim cutoff shorts for summer beach vibes", "image_url": "https://picsum.photos/seed/cutoff-shorts/400/400", "product_url": "https://www2.hm.com/en_us/productpage.008.html", "source": "HM"},
    {"name": "Tailored Wool Pants", "brand": "Nordstrom", "price": 120.00, "color": "Charcoal", "description": "Tailored wool pants for a sophisticated formal look", "image_url": "https://picsum.photos/seed/wool-pants/400/400", "product_url": "https://www.nordstrom.com/s/wool-pants/006", "source": "NORDSTROM"},

    # SHOES
    {"name": "Classic White Sneakers", "brand": "Adidas", "price": 85.00, "color": "White", "description": "Clean white leather sneakers for everyday casual wear", "image_url": "https://picsum.photos/seed/white-sneakers/400/400", "product_url": "https://www.amazon.com/dp/B007", "source": "AMAZON"},
    {"name": "Chelsea Boots", "brand": "Nordstrom", "price": 150.00, "color": "Black", "description": "Sleek black leather chelsea boots for formal and date-night looks", "image_url": "https://picsum.photos/seed/chelsea-boots/400/400", "product_url": "https://www.nordstrom.com/s/chelsea-boots/007", "source": "NORDSTROM"},
    {"name": "Running Shoes", "brand": "Nike", "price": 120.00, "color": "Black", "description": "High-performance running shoes for athletic training", "image_url": "https://picsum.photos/seed/running-shoes/400/400", "product_url": "https://www.amazon.com/dp/B008", "source": "AMAZON"},
    {"name": "Strappy Sandals", "brand": "H&M", "price": 24.99, "color": "Tan", "description": "Minimalist strappy sandals for summer beach days", "image_url": "https://picsum.photos/seed/sandals/400/400", "product_url": "https://www2.hm.com/en_us/productpage.009.html", "source": "HM"},
    {"name": "Suede Loafers", "brand": "Nordstrom", "price": 95.00, "color": "Brown", "description": "Classic suede loafers with a timeless elegant finish", "image_url": "https://picsum.photos/seed/loafers/400/400", "product_url": "https://www.nordstrom.com/s/suede-loafers/008", "source": "NORDSTROM"},
    {"name": "Platform Sneakers", "brand": "Converse", "price": 75.00, "color": "Black", "description": "Retro platform sneakers with a 90s throwback vibe", "image_url": "https://picsum.photos/seed/platform-sneakers/400/400", "product_url": "https://www.amazon.com/dp/B009", "source": "AMAZON"},
    {"name": "Block Heel Pumps", "brand": "Nordstrom", "price": 110.00, "color": "Red", "description": "Statement block heel pumps for a romantic evening out", "image_url": "https://picsum.photos/seed/block-heels/400/400", "product_url": "https://www.nordstrom.com/s/block-heels/009", "source": "NORDSTROM"},
    {"name": "Canvas Slip-Ons", "brand": "Vans", "price": 50.00, "color": "Navy", "description": "Classic canvas slip-on shoes for casual everyday wear", "image_url": "https://picsum.photos/seed/slip-ons/400/400", "product_url": "https://www.amazon.com/dp/B010", "source": "AMAZON"},
    {"name": "Ankle Boots", "brand": "H&M", "price": 49.99, "color": "Black", "description": "Versatile ankle boots with a bohemian western flair", "image_url": "https://picsum.photos/seed/ankle-boots/400/400", "product_url": "https://www2.hm.com/en_us/productpage.010.html", "source": "HM"},
    {"name": "Espadrille Wedges", "brand": "Nordstrom", "price": 85.00, "color": "Tan", "description": "Summer espadrille wedge sandals with tropical vibes", "image_url": "https://picsum.photos/seed/espadrilles/400/400", "product_url": "https://www.nordstrom.com/s/espadrilles/010", "source": "NORDSTROM"},

    # ACCESSORIES
    {"name": "Leather Crossbody Bag", "brand": "H&M", "price": 29.99, "color": "Brown", "description": "Compact leather crossbody bag for everyday casual use", "image_url": "https://picsum.photos/seed/crossbody-bag/400/400", "product_url": "https://www2.hm.com/en_us/productpage.011.html", "source": "HM"},
    {"name": "Aviator Sunglasses", "brand": "Ray-Ban", "price": 163.00, "color": "Gold", "description": "Iconic aviator sunglasses with a retro vintage look", "image_url": "https://picsum.photos/seed/aviator-sunglasses/400/400", "product_url": "https://www.nordstrom.com/s/aviator-sunglasses/011", "source": "NORDSTROM"},
    {"name": "Canvas Tote Bag", "brand": "Amazon Essentials", "price": 18.00, "color": "Natural", "description": "Simple canvas tote bag for casual summer outings", "image_url": "https://picsum.photos/seed/canvas-tote/400/400", "product_url": "https://www.amazon.com/dp/B011", "source": "AMAZON"},
    {"name": "Gold Chain Necklace", "brand": "Nordstrom", "price": 45.00, "color": "Gold", "description": "Delicate gold chain necklace for a minimalist elegant touch", "image_url": "https://picsum.photos/seed/gold-necklace/400/400", "product_url": "https://www.nordstrom.com/s/gold-necklace/012", "source": "NORDSTROM"},
    {"name": "Baseball Cap", "brand": "Nike", "price": 28.00, "color": "Black", "description": "Classic baseball cap for sporty streetwear looks", "image_url": "https://picsum.photos/seed/baseball-cap/400/400", "product_url": "https://www.amazon.com/dp/B012", "source": "AMAZON"},
    {"name": "Leather Belt", "brand": "H&M", "price": 19.99, "color": "Black", "description": "Classic leather belt with minimalist silver buckle", "image_url": "https://picsum.photos/seed/leather-belt/400/400", "product_url": "https://www2.hm.com/en_us/productpage.012.html", "source": "HM"},
    {"name": "Wool Scarf", "brand": "Nordstrom", "price": 58.00, "color": "Burgundy", "description": "Soft wool scarf in rich burgundy for cozy winter layering", "image_url": "https://picsum.photos/seed/wool-scarf/400/400", "product_url": "https://www.nordstrom.com/s/wool-scarf/013", "source": "NORDSTROM"},
    {"name": "Straw Beach Hat", "brand": "H&M", "price": 14.99, "color": "Natural", "description": "Wide-brim straw hat for tropical summer beach days", "image_url": "https://picsum.photos/seed/straw-hat/400/400", "product_url": "https://www2.hm.com/en_us/productpage.013.html", "source": "HM"},
    {"name": "Minimalist Watch", "brand": "Daniel Wellington", "price": 179.00, "color": "Silver", "description": "Clean minimalist watch with leather strap for formal occasions", "image_url": "https://picsum.photos/seed/minimalist-watch/400/400", "product_url": "https://www.amazon.com/dp/B013", "source": "AMAZON"},
    {"name": "Bohemian Earrings", "brand": "Nordstrom", "price": 32.00, "color": "Gold", "description": "Statement bohemian dangle earrings with natural stone accents", "image_url": "https://picsum.photos/seed/boho-earrings/400/400", "product_url": "https://www.nordstrom.com/s/boho-earrings/014", "source": "NORDSTROM"},
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
