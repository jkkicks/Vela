# Quick Start Guide

Get Vela running in 5 minutes!

## Prerequisites

- Python 3.9 or higher
- Discord Bot Token
- Git

## 1. Clone and Setup (1 minute)

```bash
# Clone the repository
git clone https://github.com/jkkicks/Vela.git
cd Vela

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

## 2. Install Dependencies (2 minutes)

```bash
# Install Python packages
pip install -r requirements.txt

# Download web interface assets
python download_assets.py
```

## 3. Configure (1 minute)

```bash
# Copy example configuration
cp .env.example .env

# Edit .env file with your bot token
# Minimum required: BOT_TOKEN=your_token_here
```

Or use the automatic setup:
```bash
python start.py  # Will create .env and generate encryption key
```

## 4. Run Vela (1 minute)

```bash
python -m src.main
```

Or use the startup script:
```bash
python start.py
```

## 5. Complete Web Setup

1. Open your browser to http://localhost:8000/setup
2. Enter your Discord configuration:
   - Guild ID (your Discord server ID)
   - Bot Token
   - Your Discord User ID (to make yourself admin)
3. Click "Complete Setup"

## ✅ That's It!

Your bot should now be:
- Connected to Discord
- Web interface available at http://localhost:8000
- Ready to onboard users

## Next Steps

- [Configure Discord OAuth](discord-setup.md) for web login
- [Read the full installation guide](installation.md) for detailed options
- [Check bot commands](../api/bot-commands.md)
- [Explore the web interface](../api/web-api.md)

## Need Help?

- Check [Troubleshooting Guide](troubleshooting.md)
- Visit [GitHub Issues](https://github.com/jkkicks/Vela/issues)
- Read the [FAQ](faq.md)