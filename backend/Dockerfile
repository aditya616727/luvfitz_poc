FROM python:3.12-slim

WORKDIR /app

# System deps for Camoufox (Firefox-based stealth browser) & Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    # Camoufox / Firefox dependencies
    libgtk-3-0t64 \
    libdbus-glib-1-2 \
    libxt6t64 \
    libx11-xcb1 \
    libasound2t64 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxfixes3 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers + pre-download Camoufox Firefox
RUN playwright install chromium --with-deps || true
RUN python -c "from camoufox.pkgman import installed_verstr; print('Camoufox:', installed_verstr() or 'downloading...'); import camoufox; camoufox.sync_api" 2>/dev/null || \
    python -c "import camoufox" 2>/dev/null || \
    echo "Camoufox pre-download skipped (will download on first use)"

# App code
COPY . .

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
