# Multi-stage build: dependencies installed in a builder stage so the runtime image
# stays lean and the pip layer is cached independently of app code.
FROM python:3.10-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Build deps first (cached unless requirements change).
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

# Non-root user (least privilege; containers must not run as root on ECS).
RUN groupadd --system app && useradd --system --gid app --home /workspace app

# Copy installed deps from the builder stage.
COPY --from=builder /install /usr/local

# App code (excludes .env, caches, scratch via .dockerignore).
COPY . .

# Writable dirs for the non-root app user (media fallback, etc.).
RUN mkdir -p /workspace/static /workspace/cache && chown -R app:app /workspace

USER app

EXPOSE 5000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000}"]
