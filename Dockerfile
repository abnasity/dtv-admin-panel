# Use official slim Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies
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
 && rm -rf /var/lib/apt/lists/*


# Install wkhtmltopdf (contains wkhtmltoimage) — use static binary
RUN wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.4/wkhtmltox-0.12.4_linux-generic-amd64.tar.xz && \
    tar -xJf wkhtmltox-0.12.4_linux-generic-amd64.tar.xz && \
    mv wkhtmltox/bin/wkhtmlto* /usr/local/bin/ && \
    chmod +x /usr/local/bin/wkhtmlto* && \
    rm -rf wkhtmltox*



# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# Copy project files
COPY . .

# Expose port
EXPOSE 5000

# Start the app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
