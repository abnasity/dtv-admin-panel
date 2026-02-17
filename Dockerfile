# Pinned to the most stable Debian release (Bookworm) for Python 3.10
FROM python:3.10-slim-bookworm

# Set environment variables for production stability
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies with standard Bookworm naming conventions
# This ensures libpango and libgdk-pixbuf are found correctly
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    # WeasyPrint Core Dependencies
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    # Support for images and fonts
    libjpeg-dev \
    libopenjp2-7-dev \
    shared-mime-info \
    fonts-liberation \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway dynamic port binding
EXPOSE 8080

# Use the shell form for CMD to properly expand the $PORT variable provided by Railway
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 wsgi:app"]