# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────────────────────
# Builder stage - install dependencies
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS builder

# Install uv for fast package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e ".[dev]"

# ─────────────────────────────────────────────────────────────────────────────
# Production stage
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS production

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Create non-root user
RUN useradd --create-home --shell /bin/bash waasp
USER waasp

# Expose port
EXPOSE 8000

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "waasp.app:create_app()"]

# ─────────────────────────────────────────────────────────────────────────────
# Development stage
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS development

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy all code (including tests)
COPY . .

# Development command
CMD ["flask", "--app", "waasp.app:create_app", "run", "--host", "0.0.0.0", "--port", "8000", "--debug"]
