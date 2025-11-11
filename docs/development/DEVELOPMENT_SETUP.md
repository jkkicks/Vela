# Development Setup Guide

This guide will help you set up Vela for development on Windows, macOS, or Linux.

## Prerequisites

- Python 3.9 or higher (including Python 3.13+)
- Git
- PostgreSQL (optional for local development, can use SQLite for testing)

## Setting Up Your Development Environment

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Vela
```

### 2. Create a Virtual Environment

#### Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### Windows (Command Prompt):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

**IMPORTANT: First upgrade pip and clear cache (especially for Python 3.13+):**
```bash
python -m pip install --upgrade pip setuptools wheel
pip cache purge
```

Then install all dependencies:
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure it:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- Discord bot token
- Database connection string
- Other API keys and settings

## Requirements File

The `requirements.txt` contains all dependencies needed for development and production:
- Uses `psycopg2-binary>=2.9.11` for easy installation across all platforms
- Includes development tools (pytest, black, ruff)
- Works on Windows, macOS, and Linux without compilation

## Database Setup

### For Development (SQLite)
If you want to use SQLite for quick local testing:
1. Update your `.env` file with:
   ```
   DATABASE_URL=sqlite:///./vela.db
   ```

### For Development (PostgreSQL)
If you want to use PostgreSQL locally:
1. Install PostgreSQL for your platform
2. Create a database:
   ```sql
   CREATE DATABASE vela;
   ```
3. Update your `.env` file with:
   ```
   DATABASE_URL=postgresql://username:password@localhost/vela
   ```

### Run Migrations
```bash
alembic upgrade head
```

## Common Issues and Solutions

### Issue: ModuleNotFoundError: No module named 'audioop' (Python 3.13)
**Cause**: discord.py versions before 2.4.0 depend on the `audioop` module which was removed in Python 3.13
**Solution**:
```bash
pip install --upgrade discord.py
```
This will install discord.py 2.4.0+ which is compatible with Python 3.13.

### Issue: psycopg2-binary tries to build from source (.tar.gz) instead of using wheels
**Cause**: Outdated pip version or corrupted cache, especially on Python 3.13+
**Solution**:
```bash
python -m pip install --upgrade pip setuptools wheel
pip cache purge
pip install psycopg2-binary
```

### Issue: pg_config executable not found
**Cause**: Trying to install `psycopg2` (not psycopg2-binary) without PostgreSQL development headers.
**Solution**: Use `psycopg2-binary>=2.9.11` which has pre-compiled wheels for all platforms.

### Issue: Permission denied activating venv on macOS/Linux
**Solution**:
```bash
chmod +x .venv/bin/activate
source .venv/bin/activate
```

### Issue: PowerShell execution policy on Windows
**Solution**: Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Docker Setup (Alternative)

If you prefer using Docker:

```bash
docker-compose up -d
```

This will set up the entire environment including PostgreSQL.

## Testing Your Setup

Run the test installation script:
```bash
python test_install.py
```

This will verify that all dependencies are correctly installed.

## Next Steps

1. Configure your Discord bot in the Discord Developer Portal
2. Set up OAuth2 redirects for the web interface
3. Run the bot: `python start.py`
4. Access the web interface at `http://localhost:8000`

## Troubleshooting

If you encounter any issues:
1. Ensure your Python version is 3.9+: `python --version`
2. Try creating a fresh virtual environment
3. Clear pip cache: `pip cache purge`
4. Check the project's GitHub issues or create a new one

## Notes on psycopg2-binary

- We use `psycopg2-binary>=2.9.11` for all environments
- Pre-compiled wheels available for Windows, macOS, and Linux
- No compilation required - works out of the box
- Suitable for both development and production
- For extremely high-traffic production environments, you can optionally compile `psycopg2` from source, but for most use cases psycopg2-binary is perfectly fine