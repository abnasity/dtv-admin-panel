FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (including pycairo build deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libx11-dev \
    libxcomposite-dev \
    libxrandr-dev \
    libxcursor-dev \
    libxdamage-dev \
    libxtst-dev \
    xfonts-75dpi \
    xfonts-base \
    ca-certificates \
    pkg-config \
    libcairo2-dev \
    && apt-get clean \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port (optional, for local dev)
EXPOSE 8000

# Start the app with Gunicorn
CMD ["gunicorn", "wsgi:app"]
