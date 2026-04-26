FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-worker.txt .
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY scanner.py parakeet_server.py ./
COPY scanner_app ./scanner_app
COPY data ./data
COPY feeds.txt ./feeds.txt

CMD ["python", "scanner.py"]
