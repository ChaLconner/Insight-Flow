# Multi-Stage Production Dockerfile - Staff/Principal Level
#
# Features:
# - Multi-stage build for minimal image size
# - Non-root user for security
# - Health check configuration
# - Build-time caching optimization
# - Production-ready gunicorn configuration

# =============================================================================
# Stage 1: Builder - Install dependencies and create wheels
# =============================================================================
FROM python:3.12-slim@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65 AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Create wheels for faster installation in production stage
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# =============================================================================
# Stage 2: Production - Minimal runtime image
# =============================================================================
FROM python:3.12-slim@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65 AS production

# Labels for container metadata
LABEL maintainer="Insight Flow Team" \
      version="1.0.0" \
      description="Insight Flow Backend API"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # Gunicorn settings
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=120 \
    # Application settings
    PORT=8000

# Install runtime dependencies and create the non-root runtime user.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/logs /app/static \
    && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health/ready || exit 1

# Default command - Gunicorn with Uvicorn workers
CMD ["sh", "-c", "gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${GUNICORN_WORKERS} \
    --threads ${GUNICORN_THREADS} \
    --timeout ${GUNICORN_TIMEOUT} \
    --bind 0.0.0.0:${PORT} \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance"]

# =============================================================================
# Stage 3: Development - With dev dependencies
# =============================================================================
FROM production AS development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    httpx \
    mypy \
    ruff

USER appuser

# Override command for development
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
