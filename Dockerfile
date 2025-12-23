FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Optional AI deps (do not fail the image build if unavailable)
COPY requirements-ai.txt /app/requirements-ai.txt
RUN if [ -f requirements-ai.txt ]; then pip install --no-cache-dir -r requirements-ai.txt || true; fi

COPY . /app
