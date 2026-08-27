FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV headless + psycopg + downloading models
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 wget unzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install InsightFace buffalo_s model (avoids runtime download and OOM)
RUN wget -q -O /tmp/buffalo_s.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_s.zip && \
    mkdir -p /root/.insightface/models/buffalo_s && \
    unzip -q /tmp/buffalo_s.zip -d /root/.insightface/models/buffalo_s && \
    rm /tmp/buffalo_s.zip

COPY . .
RUN chmod +x render-entrypoint.sh

EXPOSE 8000
CMD ["./render-entrypoint.sh"]
