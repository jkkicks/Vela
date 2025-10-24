# Docker Deployment Guide

Deploy SparkBot using Docker for consistent, reproducible deployments.

## Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (included with Docker Desktop)
- Basic understanding of Docker concepts

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jkkicks/SparkBot.git
   cd SparkBot
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f
   ```

5. **Access the application**:
   - Web Interface: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Configuration Options

### docker-compose.yml

The default configuration includes:
- PostgreSQL database
- SparkBot application
- Persistent volumes for data

#### Using SQLite Instead

To use SQLite instead of PostgreSQL:

```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: sparkbot
    env_file:
      - .env
    environment:
      DATABASE_URL: sqlite:///./data/sparkbot.db
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

#### Custom Network Configuration

```yaml
networks:
  sparkbot-network:
    driver: bridge

services:
  app:
    networks:
      - sparkbot-network
```

### Environment Variables

Create a `.env` file with:

```env
# Required
BOT_TOKEN=your_discord_bot_token
ENCRYPTION_KEY=your_generated_encryption_key

# Database (for PostgreSQL)
DATABASE_URL=postgresql://sparkbot:changeme@postgres:5432/sparkbot

# Optional
DISCORD_CLIENT_ID=your_oauth_client_id
DISCORD_CLIENT_SECRET=your_oauth_client_secret
API_SECRET_KEY=generate_a_random_secret
```

## Building Custom Image

### Build Locally

```bash
docker build -t sparkbot:custom .
```

### Build with Arguments

```bash
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  -t sparkbot:custom .
```

### Multi-stage Build (Production)

Create `Dockerfile.prod`:

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Make sure scripts in .local are callable
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000
CMD ["python", "-m", "src.main"]
```

## Container Management

### Basic Commands

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# Restart containers
docker-compose restart

# View running containers
docker-compose ps

# View logs
docker-compose logs -f app

# Execute command in container
docker-compose exec app python -m src.bot.main

# Enter container shell
docker-compose exec app bash
```

### Database Management

#### Backup PostgreSQL
```bash
docker-compose exec postgres pg_dump -U sparkbot sparkbot > backup.sql
```

#### Restore PostgreSQL
```bash
docker-compose exec -T postgres psql -U sparkbot sparkbot < backup.sql
```

#### Backup SQLite
```bash
docker-compose exec app cp /app/data/sparkbot.db /app/data/sparkbot.db.backup
```

## Production Deployment

### Using Docker Swarm

1. **Initialize swarm**:
   ```bash
   docker swarm init
   ```

2. **Create secrets**:
   ```bash
   echo "your_bot_token" | docker secret create bot_token -
   echo "your_encryption_key" | docker secret create encryption_key -
   ```

3. **Deploy stack**:
   ```bash
   docker stack deploy -c docker-compose.prod.yml sparkbot
   ```

### Using Kubernetes

See `kubernetes/` directory for Kubernetes manifests.

### Health Checks

Add health check to docker-compose.yml:

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Volumes and Data Persistence

### Important Directories

- `/app/data` - Database files (SQLite)
- `/app/logs` - Application logs
- `/app/static` - Static assets

### Backup Strategy

1. **Automated backups**:
   ```bash
   # Add to crontab
   0 2 * * * docker-compose exec app tar -czf /app/data/backup-$(date +\%Y\%m\%d).tar.gz /app/data/*.db
   ```

2. **Volume backup**:
   ```bash
   docker run --rm -v sparkbot_data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data
   ```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs app

# Check configuration
docker-compose config

# Rebuild image
docker-compose build --no-cache
```

### Permission Issues

```bash
# Fix ownership
docker-compose exec app chown -R 1000:1000 /app/data
```

### Network Issues

```bash
# Inspect network
docker network inspect sparkbot_default

# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

### Memory Issues

Add resource limits:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## Monitoring

### Using Prometheus

Add to docker-compose.yml:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
```

### Using Grafana

```yaml
services:
  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
```

## Security Best Practices

1. **Don't use root user**:
   ```dockerfile
   RUN useradd -m sparkbot
   USER sparkbot
   ```

2. **Use secrets management**:
   ```yaml
   services:
     app:
       secrets:
         - bot_token
         - db_password
   ```

3. **Limit network exposure**:
   ```yaml
   services:
     postgres:
       expose:
         - "5432"  # Only to other containers
   ```

4. **Regular updates**:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

## Next Steps

- [Production Deployment](production.md)
- [Manual Deployment](manual.md)
- [Monitoring and Logging](monitoring.md)
- [Backup and Recovery](backup.md)