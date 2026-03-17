# Mini Outfit Builder --- System Architecture & Technical Specification

## 1. System Goal

Build a system that:

-   Scrapes fashion products from **Zappos (US), Amazon (US), and SSENSE
    (US)**
-   Stores and categorizes products using **Google Apparel Taxonomy**
-   Refreshes **product price and availability daily**
-   Generates outfits automatically (**Top + Bottom + Accessory +
    Shoe**)
-   Allows users to search outfits by **vibe** (Date Night, 90s Outfit,
    Casual)
-   Displays outfits with **images and product links**

------------------------------------------------------------------------

## 2. High Level Architecture

    Fashion Websites
       │
       ▼
    Scraping Workers
       │
       ▼
    Product Normalization + Taxonomy Mapping
       │
       ▼
    Product Database (PostgreSQL)
       │
       ▼
    Daily Refresh Worker
       │
       ▼
    Outfit Engine
       │
       ▼
    Backend API (FastAPI / Flask)
       │
       ▼
    Frontend UI (React / Next.js)

------------------------------------------------------------------------

## 3. Technology Stack

### Backend

-   FastAPI / Flask
-   Python Scrapers (Scrapy / Playwright)
-   Celery / Workers
-   PostgreSQL
-   Redis
-   Elasticsearch (optional)

### Frontend

-   React / Next.js
-   Tailwind CSS

### Infrastructure

-   Docker
-   AWS / GCP
-   Optional S3 for caching images

------------------------------------------------------------------------

## 4. Data Scraping System

Each retailer has its own scraper module.

    scrapers/
       zappos_scraper.py
       amazon_scraper.py
       ssense_scraper.py

### Scraper Workflow

    Fetch Product List
         ↓
    Visit Product Page
         ↓
    Extract Attributes
         ↓
    Normalize Product
         ↓
    Save to Database

### Product Attributes

  Field          Description
  -------------- ---------------------------------
  name           Product name
  price          Current price
  brand          Brand name
  color          Product color
  description    Product description
  image_url      Image link
  product_url    Retail product link
  category       Top / Bottom / Shoe / Accessory
  taxonomy       Google taxonomy category
  availability   In stock or not
  source         Website source

------------------------------------------------------------------------

## 5. Google Taxonomy Mapping

Products are mapped to Google's apparel taxonomy.

Example:

    Apparel & Accessories
       Clothing
          Shirts
          Pants
          Dresses
          Jackets

Mapping rules example:

``` python
if "shirt" in name:
    taxonomy = "Apparel & Accessories > Clothing > Shirts"

if "jeans" in name:
    taxonomy = "Apparel & Accessories > Clothing > Pants"
```

Rules stored in:

    taxonomy_rules.json

------------------------------------------------------------------------

## 6. Database Design

### Products Table

  Column         Type
  -------------- -----------
  id             uuid
  name           text
  brand          text
  price          float
  color          text
  description    text
  image_url      text
  product_url    text
  category       enum
  taxonomy       text
  availability   boolean
  source         text
  last_updated   timestamp

### Category Enum

    TOP
    BOTTOM
    SHOE
    ACCESSORY

### Outfits Table

  Column         Type
  -------------- ----------
  id             uuid
  top_id         FK
  bottom_id      FK
  shoe_id        FK
  accessory_id   FK
  style_tags     text\[\]
  score          float

------------------------------------------------------------------------

## 7. Price Refresh Pipeline

Daily job to ensure **fresh prices and working links**.

    Scheduler (Cron)
          ↓
    Refresh Worker
          ↓
    Fetch Product Page
          ↓
    Extract Price + Availability
          ↓
    Update Database

Example pseudo-code:

``` python
for product in products:
    page = fetch(product.url)
    new_price = extract_price(page)
    availability = extract_stock(page)
    update(product)
```

------------------------------------------------------------------------

## 8. Outfit Builder Engine

Goal: Create outfits with

    Top + Bottom + Shoe + Accessory

Example logic:

``` python
tops = get_products("TOP")
bottoms = get_products("BOTTOM")
shoes = get_products("SHOE")
accessories = get_products("ACCESSORY")
```

Combine using rules.

Example:

    Casual Top → Jeans / Shorts
    Formal Shirt → Formal Pants
    Jeans → Sneakers

------------------------------------------------------------------------

## 9. Vibe Search System

Products and outfits are tagged with style labels.

Example tags:

    date-night
    streetwear
    retro
    summer
    casual

Search example:

    User query: "date night"
    → return outfits tagged with "date-night"

Optional improvement:

-   Sentence embeddings
-   Vector search

------------------------------------------------------------------------

## 10. Backend API Design

### Search Outfits

    GET /outfits/search?q=date-night

### Get Products

    GET /products

### Get Specific Outfit

    GET /outfits/{id}

Response includes product images, price, and product links.

------------------------------------------------------------------------

## 11. Frontend UI

UI components:

-   Search bar
-   Outfit display
-   Product images
-   Clickable product links

Example layout:

    Search: [ Date Night ]

    Generated Outfit

    [ Top Image ]
    [ Bottom Image ]
    [ Shoe Image ]
    [ Accessory Image ]

------------------------------------------------------------------------

## 12. Likeability Model (Future)

Goal: rank outfits based on aesthetic compatibility.

Features:

-   color harmony
-   brand compatibility
-   price similarity
-   style tags
-   user engagement (clicks, likes)

Possible models:

-   Logistic Regression
-   XGBoost

------------------------------------------------------------------------

## 13. Scalability

Future microservices:

    Scraper Service
    Product Service
    Outfit Service
    Search Service

Message queues:

-   Kafka
-   RabbitMQ

Used for:

-   scraping jobs
-   refresh jobs

------------------------------------------------------------------------

## 14. Backend Folder Structure

    outfit-builder/

    scrapers/
    workers/
    services/
    models/
    api/
    utils/

    main.py

------------------------------------------------------------------------

## 15. End-to-End Flow

    1. Scrapers collect 300 products
    2. Products categorized via taxonomy
    3. Data stored in database
    4. Daily worker refreshes price and availability
    5. Outfit engine generates combinations
    6. Backend API exposes search endpoints
    7. Frontend UI displays outfits
