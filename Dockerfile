FROM node:20-alpine AS webbuild
WORKDIR /web
COPY web/package*.json web/tsconfig.json web/vite.config.ts ./
RUN npm ci || npm install
COPY web/src ./src
COPY web/index.html ./
RUN npm run build

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (optional: build fonts/locales if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Copy built static UI
COPY --from=webbuild /web/dist ./web/dist

# Expose API port
EXPOSE 8000

# Single worker to keep model caches warm
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
