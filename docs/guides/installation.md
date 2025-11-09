# Installation Guide

Comprehensive installation instructions for Vela v2.0.

## Table of Contents
- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Detailed Steps](#detailed-steps)
- [Configuration](#configuration)
- [Verification](#verification)

## System Requirements

### Minimum Requirements
- Python 3.9 or higher
- 512MB RAM
- 100MB disk space
- Internet connection

### Recommended Requirements
- Python 3.11+
- 1GB RAM
- 500MB disk space
- PostgreSQL 13+ (for production)

### Operating System Support
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Ubuntu 20.04+
- ✅ Debian 11+
- ✅ CentOS 8+
- ✅ Docker (any OS with Docker support)

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
git clone https://github.com/jkkicks/Vela.git
cd Vela
python start.py  # Handles everything automatically
```

### Method 2: Manual Installation

#### Step 1: Clone Repository
```bash
git clone https://github.com/jkkicks/Vela.git
cd Vela
```

#### Step 2: Create Virtual Environment

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Windows Command Prompt:**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Download static assets
python download_assets.py
```

#### Step 4: Configure Environment
```bash
# Copy example configuration
cp .env.example .env

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add this key to ENCRYPTION_KEY in .env
```

Edit `.env` file with required values:
```env
# Required
BOT_TOKEN=your_discord_bot_token
ENCRYPTION_KEY=your_generated_key

# Optional but recommended
DISCORD_CLIENT_ID=your_oauth_client_id
DISCORD_CLIENT_SECRET=your_oauth_client_secret
API_SECRET_KEY=generate_a_random_secret
```

#### Step 5: Initialize Database
```bash
# Run the application - it will create database automatically
python -m src.main
```

### Method 3: Docker Installation

```bash
# Using docker-compose (recommended)
docker-compose up -d

# Or using Docker directly
docker build -t vela .
docker run -d -p 8000:8000 --env-file .env vela
```

See [Docker Deployment Guide](../deployment/docker.md) for details.

## Configuration

### Essential Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| BOT_TOKEN | Discord bot token | Yes* | `MTIzNDU2Nzg5...` |
| ENCRYPTION_KEY | Database encryption key | Yes | Generate with Fernet |
| DATABASE_URL | Database connection string | No | `sqlite:///./vela.db` |

*Can be configured via web UI instead

### Discord OAuth Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| DISCORD_CLIENT_ID | OAuth application ID | For web login | `123456789012345678` |
| DISCORD_CLIENT_SECRET | OAuth application secret | For web login | `your_client_secret` |
| DISCORD_REDIRECT_URI | OAuth callback URL | For web login | `http://localhost:8000/auth/callback` |

### Advanced Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| API_PORT | Web interface port | 8000 |
| API_HOST | Web interface host | 0.0.0.0 |
| LOG_LEVEL | Logging verbosity | INFO |
| DEBUG | Debug mode | false |
| REDIS_URL | Redis connection (optional) | None |

## Verification

### 1. Test Installation
```bash
python test_install.py
```

Expected output:
```
Testing Vela installation...
[OK] discord.py imported
[OK] FastAPI imported
[OK] SQLModel imported
[OK] Database models imported
[OK] Configuration imported

✅ All core dependencies installed successfully!
```

### 2. Start Application
```bash
python -m src.main
```

Look for:
```
✅ Web interface available at: http://localhost:8000
📚 API documentation at: http://localhost:8000/docs
```

### 3. Check Web Interface
- Navigate to http://localhost:8000
- If first run, you'll be redirected to /setup
- Complete the setup wizard

### 4. Verify Bot Connection
- Check Discord to see if bot is online
- Try a command like `/ping`

## Troubleshooting Installation

### Python Version Issues
```bash
# Check Python version
python --version  # Should be 3.9+

# On macOS/Linux, might need python3
python3 --version
```

### Dependency Conflicts
```bash
# Clean reinstall
pip uninstall -r requirements.txt -y
pip install -r requirements.txt --force-reinstall
```

### Permission Errors
- Windows: Run as Administrator or use user install: `pip install --user -r requirements.txt`
- Linux/Mac: Don't use sudo with pip, use virtual environment

### Database Issues
- SQLite: Ensure write permissions in current directory
- PostgreSQL: Check connection string and credentials

## Next Steps

- [Configure Discord Bot](discord-setup.md)
- [First Run Setup](first-run.md)
- [Understanding the Project Structure](../development/project-structure.md)
- [Deployment Options](../deployment/README.md)