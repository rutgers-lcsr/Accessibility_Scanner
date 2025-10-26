FROM python:latest AS api

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmariadb-dev build-essential pkg-config libcairo2-dev

RUN python3 -m pip install --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

RUN rm -rf /var/lib/apt/lists/*

COPY authentication/ ./authentication/
COPY scanner/ ./scanner/
COPY blueprints/ ./blueprints/
COPY mail/ ./mail/
COPY models/ ./models/
COPY templates/ ./templates/
COPY migrations/ ./migrations/
COPY utils/ ./utils/
COPY static/ ./static/
COPY app.py .
COPY celery_app.py .
COPY config.py .
COPY init.sh .

RUN chmod +x /app/init.sh

CMD ["/app/init.sh","gunicorn", "--capture-output","--log-file=-", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]

FROM python:latest AS worker

COPY --from=api /usr/local/lib/python3.*/site-packages/ /usr/local/lib/python3.*/site-packages/
COPY --from=api /app /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmariadb-dev build-essential pkg-config libcairo2-dev

WORKDIR /app
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
RUN rm -rf /var/lib/apt/lists/*

CMD ["celery", "-A", "celery_app.celery", "worker", "--loglevel=info", "--concurrency=4"]

FROM python:latest AS flower

COPY --from=api /usr/local/lib/python3.*/site-packages/ /usr/local/lib/python3.*/site-packages/
COPY --from=api /app /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmariadb-dev build-essential pkg-config libcairo2-dev

WORKDIR /app
RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
RUN rm -rf /var/lib/apt/lists/*

CMD ["celery", "-A", "celery_app.celery", "flower", "--port=5555"]

FROM python:latest AS beat

COPY --from=api /usr/local/lib/python3.*/site-packages/ /usr/local/lib/python3.*/site-packages/
COPY --from=api /app /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmariadb-dev build-essential pkg-config libcairo2-dev

WORKDIR /app
RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN rm -rf /var/lib/apt/lists/*

# Celery Beat doesn't need Playwright
CMD ["celery", "-A", "celery_app.celery", "beat", "--loglevel=info"]
