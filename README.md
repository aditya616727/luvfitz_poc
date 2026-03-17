# 👗 Mini Outfit Builder

A production-ready fashion outfit generation system that scrapes products from **Zappos**, **Amazon**, and **SSENSE**, categorizes them using **Google Apparel Taxonomy**, and generates styled outfits searchable by **vibe** (Date Night, Streetwear, Casual, Retro, etc.).

---

## 🏗 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Zappos Scraper  │    │  Amazon Scraper   │    │ SSENSE Scraper  │
└────────┬────────┘    └────────┬─────────┘    └────────┬────────┘
         │                      │                       │
         └──────────────┬───────┴───────────────────────┘
                        ▼
            ┌───────────────────────┐
            │  Product Normalization │
            │  + Taxonomy Mapping    │
            └───────────┬───────────┘
                        ▼
            ┌───────────────────────┐
            │   PostgreSQL Database  │
            └───────────┬───────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
  ┌──────────┐  ┌──────────────┐  ┌──────────┐
  │  Daily    │  │   Outfit     │  │  FastAPI  │
  │  Refresh  │  │   Engine     │  │  Backend  │
  │  Worker   │  │  (Scoring)   │  │    API    │
  └──────────┘  └──────────────┘  └─────┬─────┘
                                        ▼
                                 ┌──────────────┐
                                 │   Next.js     │
                                 │   Frontend    │
                                 └──────────────┘
```

---

## 🛠 Tech Stack

| Layer           | Technology                           |
|-----------------|--------------------------------------|
| **Backend API** | FastAPI, Python 3.12                 |
| **Database**    | PostgreSQL 16                        |
| **Cache/Queue** | Redis 7                              |
| **Workers**     | Celery (scraping, refresh, outfits)  |
| **Scrapers**    | httpx, BeautifulSoup4                |
| **Frontend**    | Next.js 14, React 18, Tailwind CSS   |
| **Containers**  | Docker, Docker Compose               |

---

## 📁 Project Structure

```
poc_J2/
├── docker-compose.yml          # Full stack orchestration
├── docker-compose.dev.yml      # Dev overrides
├── .env.example                # Environment variables template
├── deploy.sh                   # One-command production deploy script
├── nginx/
│   └── nginx.conf              # Reverse proxy config (single port access)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI application entry point
│   ├── alembic.ini             # Database migrations config
│   ├── alembic/                # Migration scripts
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Settings from env vars
│   │   │   ├── database.py     # SQLAlchemy engine & sessions
│   │   │   └── logging.py      # Structured logging
│   │   ├── models/
│   │   │   └── models.py       # Product & Outfit ORM models
│   │   ├── schemas/
│   │   │   └── __init__.py     # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── products.py     # /api/products endpoints
│   │   │   ├── outfits.py      # /api/outfits endpoints
│   │   │   └── admin.py        # /api/admin endpoints (scrape, refresh)
│   │   ├── services/
│   │   │   ├── product_service.py   # Product CRUD + search
│   │   │   └── outfit_service.py    # Outfit generation + scoring
│   │   ├── scrapers/
│   │   │   ├── base.py         # Abstract scraper + normalization
│   │   │   ├── zappos_scraper.py
│   │   │   ├── amazon_scraper.py
│   │   │   └── ssense_scraper.py
│   │   ├── workers/
│   │   │   ├── celery_app.py   # Celery configuration + beat schedule
│   │   │   ├── scrape_tasks.py # Scraping tasks
│   │   │   ├── refresh_tasks.py # Price/availability refresh
│   │   │   └── outfit_tasks.py # Outfit generation tasks
│   │   ├── utils/
│   │   │   ├── taxonomy.py     # Google Taxonomy mapping
│   │   │   ├── taxonomy_rules.json  # Mapping rules + style keywords
│   │   │   └── colors.py       # Color harmony scoring
│   │   └── scripts/
│   │       └── seed.py         # Database seeding with sample data
│   └── tests/
│       ├── test_taxonomy.py
│       ├── test_colors.py
│       ├── test_scrapers.py
│       └── test_api.py
│
└── frontend/
    ├── Dockerfile
    ├── Dockerfile.dev
    ├── package.json
    ├── tsconfig.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    └── src/
        ├── lib/
        │   └── api.ts          # API client + TypeScript types
        └── app/
            ├── layout.tsx      # Root layout
            ├── globals.css     # Tailwind + custom styles
            ├── page.tsx        # Home page (search + outfit grid)
            └── outfit/
                └── [id]/
                    └── page.tsx # Outfit detail page
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- (Optional) Node.js 20+, Python 3.12+ for local development

### One-Command Setup (Recommended)

Cross-platform setup scripts handle everything — Docker validation, `.env` creation, building, health checks, and seeding:

| OS | Command |
|----|---------|
| **macOS / Linux** | `./setup.sh` |
| **Windows (CMD)** | `setup.bat` |
| **Windows (PowerShell)** | `.\setup.ps1` |

#### Available Flags

```bash
# macOS / Linux
./setup.sh              # Build, wait for health, seed, and start
./setup.sh --build      # Rebuild containers only
./setup.sh --seed       # Re-seed the database only
./setup.sh --stop       # Stop all containers
./setup.sh --reset      # Full reset (destroy volumes, rebuild, re-seed)
./setup.sh --status     # Show container status

# Windows CMD
setup.bat --build
setup.bat --seed
setup.bat --reset

# Windows PowerShell
.\setup.ps1 -Action build
.\setup.ps1 -Action seed
.\setup.ps1 -Action reset
```

### Manual Setup

<details>
<summary>Click to expand manual steps</summary>

#### 1. Clone & Configure

```bash
cd poc_J2
cp .env.example .env
```

#### 2. Start Everything

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`
- **Backend API** on port `8000`
- **Celery Worker** (background tasks)
- **Celery Beat** (scheduled tasks)
- **Frontend** on port `3000`

#### 3. Seed the Database

```bash
docker compose exec backend python -m app.scripts.seed
```

This populates the database with **40 sample products** across all categories and generates **~38 outfits**.

#### 4. Open the App

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

</details>

---

## 🌐 Deploy to a Remote Server (Access from Anywhere)

The app includes an **Nginx reverse proxy** that serves both the frontend and backend API through a single port (default: **80**), so you can access everything from any device.

### 1. Copy the project to your server

```bash
scp -r poc_J2 user@your-server-ip:~/poc_J2
# or clone from your git repo
```

### 2. Run the deploy script

```bash
cd poc_J2
./deploy.sh
```

On first run, it creates a `.env` file for you to configure. Edit it, then run `./deploy.sh` again.

### 3. Open firewall port 80 (if needed)

```bash
# AWS EC2: Add inbound rule for port 80 in Security Group
# GCP: gcloud compute firewall-rules create allow-http --allow tcp:80
# Ubuntu UFW:
sudo ufw allow 80/tcp
```

### 4. Access from anywhere

| Service     | URL                                    |
|-------------|----------------------------------------|
| **App**     | `http://YOUR_SERVER_IP`                |
| **API Docs**| `http://YOUR_SERVER_IP/docs`           |
| **Health**  | `http://YOUR_SERVER_IP/health`         |

### 5. Seed data on the server

```bash
docker compose exec backend python -m app.scripts.seed
```

### Architecture with Nginx Proxy

```
  Internet
     │
     ▼
┌─────────┐      ┌───────────┐      ┌───────────┐
│  Nginx  │─────▶│  Next.js  │      │ PostgreSQL│
│  :80    │      │  Frontend │      │           │
│         │      └───────────┘      └───────────┘
│         │                               ▲
│  /api/* │──▶┌───────────┐               │
│  /docs  │   │  FastAPI   │──────────────┘
│  /health│   │  Backend   │──▶ Redis
└─────────┘   └───────────┘
```

---

## 🔌 API Endpoints

### Public Endpoints

| Method | Endpoint                    | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | `/api/outfits/search?q=`    | Search outfits by vibe             |
| GET    | `/api/outfits`              | List all outfits (paginated)       |
| GET    | `/api/outfits/{id}`         | Get outfit by ID                   |
| GET    | `/api/products`             | List products (filterable)         |
| GET    | `/api/products/search?q=`   | Search products by name            |
| GET    | `/api/products/stats`       | Product count by category          |
| GET    | `/api/products/{id}`        | Get product by ID                  |

### Admin Endpoints

| Method | Endpoint                          | Description                       |
|--------|-----------------------------------|-----------------------------------|
| POST   | `/api/admin/scrape?source=all`    | Trigger scraping tasks            |
| POST   | `/api/admin/refresh`              | Trigger price/availability refresh|
| POST   | `/api/admin/generate-outfits`     | Generate outfit combinations      |
| POST   | `/api/admin/generate-outfits-sync`| Sync generation (dev)             |

### Query Parameters

- **`q`** – Search/vibe query (e.g., `date-night`, `casual`, `retro`)
- **`category`** – Filter: `TOP`, `BOTTOM`, `SHOE`, `ACCESSORY`
- **`source`** – Filter: `ZAPPOS`, `AMAZON`, `SSENSE`
- **`min_price` / `max_price`** – Price range filter
- **`page` / `per_page`** – Pagination

---

## 👔 Outfit Generation

The outfit engine creates combinations of **Top + Bottom + Shoe + Accessory** using:

1. **Style Compatibility** – Products must share compatible style tags
2. **Color Harmony** – Colors scored based on a color wheel model (40% weight)
3. **Price Similarity** – Similar price ranges score higher (20% weight)
4. **Style Coherence** – More shared style tags = higher score (30% weight)
5. **Brand Diversity** – Mix of brands adds variety (10% weight)

### Supported Vibes

| Vibe | Keywords |
|------|----------|
| 🌹 Date Night | date, romantic, evening, cocktail |
| ☀️ Casual | casual, everyday, relaxed, comfortable |
| 🔥 Streetwear | street, urban, oversized, graphic |
| 📼 Retro | retro, vintage, 90s, 80s, throwback |
| ◻️ Minimalist | minimal, clean, simple, neutral |
| 🏖️ Summer | summer, tropical, beach, lightweight |
| 🌻 Boho | bohemian, earthy, natural, flowy |
| 👔 Formal | formal, elegant, office, professional |
| 🏃 Sporty | sport, athletic, gym, active |
| ❄️ Winter | winter, cozy, warm, layered |

---

## 🔄 Daily Refresh Pipeline

The Celery beat scheduler runs daily at **3 AM UTC**:

1. **Price Refresh** – Re-fetches product pages to update prices
2. **Availability Check** – Marks products as unavailable if pages return 404
3. **Outfit Regeneration** – Runs at **4 AM UTC** after refresh completes

Manual triggers available via the admin API.

---

## 🧪 Testing

```bash
# Run all tests
docker compose exec backend python -m pytest tests/ -v

# Run specific test file
docker compose exec backend python -m pytest tests/test_taxonomy.py -v

# Run with coverage
docker compose exec backend python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## 🛠 Local Development (Without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Needs PostgreSQL and Redis running locally
export DATABASE_URL=postgresql://outfit_user:outfit_secret_pw@localhost:5432/outfit_builder
export REDIS_URL=redis://localhost:6379/0

# Run API
uvicorn main:app --reload --port 8000

# Run worker
celery -A app.workers.celery_app worker --loglevel=info

# Seed data
python -m app.scripts.seed
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## 📦 Deployment

### Production Docker

```bash
docker compose -f docker-compose.yml up --build -d
```

### Environment Variables

See `.env.example` for all configuration options. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...@postgres:5432/outfit_builder` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/1` |
| `APP_ENV` | Environment | `development` |
| `NEXT_PUBLIC_API_URL` | Backend API URL for frontend | `http://localhost:8000` |

---

## 📋 Future Improvements

- [ ] **Likeability Model** – ML scoring using user engagement data (XGBoost)
- [ ] **Vector Search** – Sentence embeddings for semantic vibe matching
- [ ] **Image Caching** – S3 bucket for product image proxying
- [ ] **User Accounts** – Save favorite outfits, like/dislike
- [ ] **Elasticsearch** – Full-text search upgrade
- [ ] **Microservices** – Split into Scraper/Product/Outfit/Search services
- [ ] **Message Queues** – Kafka/RabbitMQ for inter-service communication
- [ ] **CI/CD** – GitHub Actions pipeline
- [ ] **Rate Limiting** – API rate limiting with Redis
- [ ] **Image Generation** – AI outfit mood boards

---