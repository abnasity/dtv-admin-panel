FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Port 8080 is common for Railway, but we'll use a variable for flexibility
ENV PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies for WeasyPrint and Cairo
# We group these to keep the image layers clean
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    shared-mime-info \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    # Fonts are often needed for WeasyPrint to render text correctly
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Railway ignores EXPOSE, but it's good practice
EXPOSE 8080

# Start the app. 
# Using --bind 0.0.0.0:$PORT allows Railway to dynamically assign the port.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} wsgi:app"]