# PAKE System Production Dockerfile - Optimized Layer Caching
# Single-stage build with optimized dependency installation order

FROM python:3.12.8-slim

# Set environment variables for security and performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# Set work directory
WORKDIR /app

# Install system dependencies with security updates
# This layer changes infrequently, so it's cached well
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    pkg-config \
    libpq-dev \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy dependency files first for optimal layer caching
# This layer only changes when dependencies change
COPY requirements.txt .

# Install Python dependencies
# This layer is cached unless requirements.txt changes
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
# This layer changes infrequently
RUN useradd -m -u 1000 pake

# Create necessary directories with proper permissions
RUN mkdir -p /app/vault /app/logs && \
    chown -R pake:pake /app && \
    chmod 700 /app/vault

# Copy application code last
# This layer changes most frequently but doesn't invalidate dependency layers
COPY --chown=pake:pake . .

# Switch to non-root user
USER pake

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "mcp_server_standalone.py"]
