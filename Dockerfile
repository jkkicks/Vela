FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including tini for proper signal handling)
RUN apt-get update && apt-get install -y \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Create data directory and set as volume
RUN mkdir -p /app/data
VOLUME ["/app/data"]

# Set environment variables for proper signal handling and output
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Use tini as entrypoint for proper signal handling
ENTRYPOINT ["tini", "--"]

# Run the application
CMD ["python", "-m", "src.main"]