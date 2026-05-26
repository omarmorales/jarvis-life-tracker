# Use the official lightweight Python slim image
FROM python:3.12-slim

# Set system environment variables to optimize Python running inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (required for Postgres drivers and compilation utilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to utilize Docker layer caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Expose port 8000 for FastAPI
EXPOSE 8000

# Default command to run the Uvicorn FastAPI server on container startup
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
