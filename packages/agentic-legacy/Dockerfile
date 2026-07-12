# Agentic AI System - Docker Configuration
# Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩

FROM python:3.12-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libxss1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    fonts-liberation \
    libappindicator3-1 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` \
    && wget -N http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && rm chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs temp reports config \
    && chmod 755 data logs temp reports config

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=web_interface/app.py
ENV SELENIUM_DRIVER_PATH=/usr/local/bin/chromedriver
ENV DISPLAY=:99

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/system/status || exit 1

# Development stage
FROM base as development
ENV FLASK_ENV=development
ENV FLASK_DEBUG=true
CMD ["python", "start_system.py", "--development"]

# Production stage
FROM base as production
ENV FLASK_ENV=production
ENV FLASK_DEBUG=false

# Create non-root user for security
RUN groupadd -r agentic && useradd -r -g agentic agentic \
    && chown -R agentic:agentic /app
USER agentic

# Start application
CMD ["python", "start_system.py", "--production"]

# Multi-architecture support
# docker buildx build --platform linux/amd64,linux/arm64 -t agentic-ai:latest .
