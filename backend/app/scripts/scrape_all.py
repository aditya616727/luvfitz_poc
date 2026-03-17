"""
Run scrapers directly and populate the database.
Usage: python -m app.scripts.scrape_all
"""

import asyncio
from app.core.database import SessionLocal, engine, Base
from app.core.logging import logger
from app.services.product_service import ProductService
from app.services.outfit_service import OutfitService
from app.scrapers.zappos_scraper import ZapposScraper
from app.scrapers.amazon_scraper import AmazonScraper
from app.scrapers.ssense_scraper import SSENSEScraper


async def run_scrapers(max_per_source: int = 100):
    """Run all scrapers and return normalized products."""
    all_products = []

    scrapers = [
        ("Zappos", ZapposScraper()),
        ("Amazon", AmazonScraper()),
        ("SSENSE", SSENSEScraper()),
    ]

    for name, scraper in scrapers:
        try:
            logger.info(f"Starting {name} scraper...")
            products = await scraper.scrape_and_normalize(max_per_source)
            valid = [p for p in products if p.category is not None]
            logger.info(f"{name}: scraped {len(products)}, normalized {len(valid)} products")
            all_products.extend(valid)
        except Exception as e:
            logger.error(f"{name} scraper failed: {e}")

    return all_products


def store_products(products):
    """Store scraped products in the database."""
    # Drop and recreate tables (source_enum changed)
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS outfits CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS source_enum CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS category_enum CASCADE"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables recreated with new source enum")

    db = SessionLocal()
    try:
        service = ProductService(db)
        count = 0
        for p in products:
            try:
                service.upsert(p.to_dict())
                count += 1
            except Exception as e:
                logger.error(f"Failed to store {p.name}: {e}")
                db.rollback()
        logger.info(f"Stored {count} products in database")
        return count
    finally:
        db.close()


def generate_outfits(max_outfits: int = 100):
    """Generate outfit combinations from stored products."""
    db = SessionLocal()
    try:
        service = OutfitService(db)
        generated = service.generate_outfits(max_outfits)
        logger.info(f"Generated {generated} outfits")
        return generated
    finally:
        db.close()


def main():
    logger.info("=" * 60)
    logger.info("SCRAPING ALL SOURCES")
    logger.info("=" * 60)

    # Run scrapers
    products = asyncio.run(run_scrapers(max_per_source=200))
    logger.info(f"Total scraped products: {len(products)}")

    # Store in DB
    stored = store_products(products)
    logger.info(f"Total stored: {stored}")

    # Print category breakdown
    db = SessionLocal()
    try:
        service = ProductService(db)
        stats = service.count_by_category()
        logger.info(f"Category stats: {stats}")

        # Print Google taxonomy distribution
        from sqlalchemy import func as sqlfunc
        from app.models.models import Product
        tax_results = (
            db.query(Product.google_product_category, sqlfunc.count(Product.id))
            .group_by(Product.google_product_category)
            .order_by(sqlfunc.count(Product.id).desc())
            .all()
        )
        logger.info("Google Product Taxonomy distribution:")
        for tax, count in tax_results:
            logger.info(f"  {tax}: {count}")
    finally:
        db.close()

    # Generate outfits
    generated = generate_outfits(max_outfits=200)

    logger.info("=" * 60)
    logger.info(f"DONE: {stored} products, {generated} outfits")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
