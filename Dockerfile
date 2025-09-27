FROM python:latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmariadb-dev build-essential pkg-config libcairo2-dev

RUN python3 -m pip install --upgrade pip

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
COPY config.py .
COPY init.sh .

RUN chmod +x ./init.sh

CMD ["./init.sh","gunicorn", "--capture-output","--log-file=-", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]