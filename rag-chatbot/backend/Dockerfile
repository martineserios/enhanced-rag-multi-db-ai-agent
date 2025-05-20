# filepath: backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    graphviz \
    graphviz-dev \
    pkg-config \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip
RUN pip install --no-cache-dir uv

# Copy only dependency file for better caching
COPY pyproject.toml ./

# Install Python dependencies using uv
# In production, we only install main dependencies and viz extras for graph visualization
RUN uv pip install --system --no-cache -e ".[viz]"

# Create necessary directories
RUN mkdir -p /app/docs/graphs /app/logs

# Copy the rest of the application
COPY . .

# Create a non-root user and set proper permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

USER appuser

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=/usr/local/bin/python \
    GRAPHVIZ_DOT=/usr/bin/dot

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]