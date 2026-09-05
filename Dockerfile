# 1. Use the same Python version as local development
FROM python:3.12-slim

# 2. Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:0.11.13 /uv /uvx /bin/

# 3. Prevent Python from buffering and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 4. Install build tools needed for gevent/greenlet
# These are essential because gevent compiles C extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Resolve the locked project environment
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# 6. Copy the application
COPY . .

# 7. Expose the port
EXPOSE 5001

# 8. Run with the locked uv environment
CMD ["uv", "run", "--frozen", "--no-dev", "python", "app.py"]