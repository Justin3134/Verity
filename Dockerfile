# ── Stage 1: Build Next.js frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY verity/frontend/package.json verity/frontend/package-lock.json* ./
RUN npm ci
COPY verity/frontend/ .
# Empty string → client-side code uses relative URLs; nginx routes them to FastAPI
ARG NEXT_PUBLIC_BACKEND_URL=""
ENV NEXT_PUBLIC_BACKEND_URL=""
RUN npm run build

# ── Stage 2: Combined runtime ─────────────────────────────────────────────────
# node:20-slim and python:3.11-slim are both debian:bookworm-slim, so the
# node binary copied here is fully compatible.
FROM python:3.11-slim

# Install nginx, supervisord, and openssl (needed by node binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx supervisor libssl3 ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Node.js binary from the official slim image (same debian base, no compat issues)
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node

# ── Python backend ────────────────────────────────────────────────────────────
WORKDIR /app/backend
COPY verity/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY verity/backend/ .

# ── Next.js standalone ────────────────────────────────────────────────────────
COPY --from=frontend-builder /build/.next/standalone /app/frontend/
COPY --from=frontend-builder /build/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /build/public /app/frontend/public

# ── Config ────────────────────────────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/app.conf

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/app.conf"]
