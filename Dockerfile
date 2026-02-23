# Pinned to the most stable Debian release (Bookworm) for Python 3.10
FROM python:3.10-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies
# Added: libpq-dev (for psycopg2) and libcairo2-dev (for pycairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libcairo2-dev \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    shared-mime-info \
    fonts-liberation \
    libffi-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# We upgrade pip and setuptools to ensure the newest wheels are used
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway dynamic port binding
EXPOSE 8080

# Start the app
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 wsgi:app"]