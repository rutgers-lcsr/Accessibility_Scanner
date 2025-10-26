# ==============================================================================
# Base stage - Common dependencies and Python packages
# ==============================================================================
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    build-essential \
    pkg-config \
    libcairo2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY authentication/ ./authentication/
COPY scanner/ ./scanner/
COPY blueprints/ ./blueprints/
COPY mail/ ./mail/
COPY models/ ./models/
COPY templates/ ./templates/
COPY migrations/ ./migrations/
COPY utils/ ./utils/
COPY static/ ./static/
COPY app.py celery_app.py config.py init.sh ./

RUN chmod +x /app/init.sh

# ==============================================================================
# Playwright stage - Adds browser dependencies (used by worker and api)
# ==============================================================================
FROM base AS playwright

# Install Playwright with Chromium
RUN playwright install --with-deps chromium && \
    # Clean up unnecessary Playwright browsers cache
    rm -rf /root/.cache/ms-playwright/*firefox* \
           /root/.cache/ms-playwright/*webkit* && \
    # Clean up apt cache
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ==============================================================================
# API stage - Flask application
# ==============================================================================
FROM playwright AS api

CMD ["/app/init.sh", "gunicorn", "--capture-output", "--log-file=-", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]

# ==============================================================================
# Worker stage - Celery worker (needs Playwright for scanning)
# ==============================================================================
FROM playwright AS worker

CMD ["celery", "-A", "celery_app.celery", "worker", "--loglevel=info", "--concurrency=4"]

# ==============================================================================
# Flower stage - Celery monitoring (doesn't need Playwright)
# ==============================================================================
FROM base AS flower

CMD ["celery", "-A", "celery_app.celery", "flower", "--port=5555"]

# ==============================================================================
# Beat stage - Celery Beat scheduler (doesn't need Playwright)
# ==============================================================================
FROM base AS beat

CMD ["celery", "-A", "celery_app.celery", "beat", "--loglevel=info"]
