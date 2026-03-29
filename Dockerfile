# ── Stage 1: Build Next.js frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY verity/frontend/package.json verity/frontend/package-lock.json* ./
RUN npm ci
COPY verity/frontend/ .
# Empty string → client-side code falls back to relative URLs (nginx routes them to FastAPI)
ARG NEXT_PUBLIC_BACKEND_URL=""
ENV NEXT_PUBLIC_BACKEND_URL=""
RUN npm run build

# ── Stage 2: Combined runtime ────────────────────────────────────────────────
FROM python:3.11-slim

# Install Node.js 20, nginx, and supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg nginx supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── Python backend ────────────────────────────────────────────────────────────
WORKDIR /app/backend
COPY verity/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY verity/backend/ .

# ── Next.js standalone build ──────────────────────────────────────────────────
COPY --from=frontend-builder /build/.next/standalone /app/frontend/
COPY --from=frontend-builder /build/.next/static /app/frontend/.next/static
RUN mkdir -p /app/frontend/public
COPY --from=frontend-builder /build/public/ /app/frontend/public/

# ── Config ────────────────────────────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/app.conf

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/app.conf"]
