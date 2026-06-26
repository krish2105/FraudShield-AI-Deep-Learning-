# FraudShield AI — backend image (FastAPI + PyTorch, serves the built React app)
# Build:  docker build -t fraudshield .
# Run:    docker run -p 8000:8000 fraudshield
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps kept minimal (CPU-only torch).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
# Install the CPU-only PyTorch wheel explicitly (no CUDA) — far smaller image.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Copy the application (web/dist is served if present; build it in CI/host).
COPY . .

EXPOSE 8000

# Container healthcheck hits the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
