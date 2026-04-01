# 1. Use 3.12-slim as requested
FROM python:3.12-slim

# 2. Prevent Python from buffering and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 3. Install build tools needed for gevent/greenlet
# These are essential because gevent compiles C extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application
COPY . .

# 6. Expose the port
EXPOSE 5001

# 7. THE FIX: Corrected CMD syntax
# CMD requires commas between arguments in exec form
CMD ["python", "app.py"]