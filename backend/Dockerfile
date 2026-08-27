FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV headless + psycopg + downloading models
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 wget unzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install InsightFace buffalo_l model (avoids runtime download)
RUN wget -q -O /tmp/buffalo_l.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip && \
    mkdir -p /root/.insightface/models/buffalo_l && \
    unzip -q /tmp/buffalo_l.zip -d /root/.insightface/models/buffalo_l && \
    rm /tmp/buffalo_l.zip

COPY . .
RUN chmod +x render-entrypoint.sh

EXPOSE 8000
CMD ["./render-entrypoint.sh"]
