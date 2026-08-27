FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV headless + psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install InsightFace buffalo_l model (avoids runtime download)
COPY buffalo_l.zip /tmp/buffalo_l.zip
RUN mkdir -p /root/.insightface/models/buffalo_l && \
    python -c "import zipfile; zipfile.ZipFile('/tmp/buffalo_l.zip').extractall('/root/.insightface/models/buffalo_l')" && \
    rm /tmp/buffalo_l.zip

COPY . .
RUN chmod +x render-entrypoint.sh

EXPOSE 8000
CMD ["./render-entrypoint.sh"]
