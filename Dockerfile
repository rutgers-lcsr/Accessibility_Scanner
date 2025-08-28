FROM playwright/chromium

RUN apt-get update && apt-get install -y

RUN python3 -m pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY authentication/ ./authentication/
COPY scanner/ ./scanner/
COPY blueprints/ ./blueprints/
COPY mail/ ./mail/
COPY models/ ./models/
COPY static/ ./static/
COPY templates/ ./templates/
COPY utils/ ./utils/
COPY app.py .
COPY config.py .
COPY init.sh .

RUN chmod +x ./init.sh

CMD ["./init.sh","gunicorn","-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]