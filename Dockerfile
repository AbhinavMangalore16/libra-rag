FROM python:3.12-slim

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy the pyproject.toml (and lockfile if present) to install dependencies
# We assume uv is being used based on the user's requirements
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache || uv sync --no-cache

# Copy application code
COPY src/ src/

# Expose port
EXPOSE 8000

# Command to run the FastAPI app
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
