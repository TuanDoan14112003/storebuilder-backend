# Base image: Python 3.13 slim version for a minimal footprint
FROM python:3.11-slim AS builder

# Set working directory for all subsequent commands
WORKDIR /app

# Python environment variables:
# Prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Install system dependencies:
# libpq-dev: Required for psycopg2 (PostgreSQL adapter)
# gcc: Required for compiling some Python packages
RUN apt-get update

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .
# Install Python dependencies without storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of application code to container
COPY . .

# Document that the container listens on port 8000
EXPOSE 8000

CMD ["sh", "-c", "gunicorn storebuilder.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
