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
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Download static assets during build
# First create the static directory
RUN mkdir -p /app/static

# Download JavaScript libraries directly in the Dockerfile
RUN curl -sSL https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js -o /app/static/htmx.min.js && \
    curl -sSL https://unpkg.com/alpinejs@3.13.3/dist/cdn.min.js -o /app/static/alpine.min.js && \
    echo '/* Custom styles for Vela */\n.htmx-indicator { display: none; }\n.htmx-request .htmx-indicator { display: inline; }\n.htmx-request.htmx-indicator { display: inline; }' > /app/static/custom.css

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