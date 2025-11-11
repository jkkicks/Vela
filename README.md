# Vela

[![GitHub Release](https://img.shields.io/github/v/release/jkkicks/Vela?include_prereleases)](https://github.com/jkkicks/Vela/releases)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://hub.docker.com/r/yourname/vela)

A modern Discord onboarding bot with a web management interface, built with FastAPI, SQLModel, and HTMX.

## What's New

- **Graceful Shutdown Handling** - Proper signal handling for both local development and Docker deployments
- **Onboarding Management from Web UI** - Approve or demote user onboarding status directly from the dashboard
- **Python 3.13+ Support** - Full compatibility with latest Python versions
- **Enhanced Notifications** - Customizable Discord event notifications with toggle controls
- **Improved Documentation** - Reorganized docs with dedicated sections for development, deployment, and API reference
- **28+ API Endpoints** - Comprehensive REST API for all bot operations

## Features

- **Discord Bot Functionality**
  - Automated member onboarding with customizable workflow
  - Nickname management based on real names
  - Role assignment upon onboarding completion
  - Persistent button/modal interactions
  - Comprehensive audit logging
  - Graceful shutdown handling for both local and Docker environments

- **Web Management Interface**
  - Discord OAuth authentication
  - User management dashboard with approve/demote onboarding status
  - Bot configuration panel
  - Real-time audit logs
  - Multi-guild support (built-in from day one)
  - Export member data (CSV/JSON)
  - Welcome message customization with notification controls
  - Command management interface

- **Technical Features**
  - Full Python 3.13+ support with discord.py 2.4.0+
  - Dual database support (SQLite/PostgreSQL)
  - HTMX for dynamic UI without JavaScript complexity
  - Docker containerization with proper signal handling (tini)
  - CI/CD with GitHub Actions
  - Fully typed with SQLModel
  - Comprehensive structured logging with graceful shutdown
  - Built-in notification system for Discord events

## 📖 Documentation

For detailed documentation, visit the [docs folder](docs/README.md):
- [Quick Start Guide](docs/guides/quick-start.md) - Get running in 5 minutes
- [Installation Guide](docs/guides/installation.md) - Detailed setup instructions
- [Discord Setup](docs/guides/discord-setup.md) - Bot and OAuth configuration
- [Development Guide](docs/development/DEVELOPMENT_SETUP.md) - Python 3.13+ setup and dependencies
- [Project Structure](docs/development/project-structure.md) - Understanding the codebase
- [Shutdown Handling](docs/development/SHUTDOWN_HANDLING.md) - Graceful shutdown procedures
- [API Reference](docs/api/) - Complete API documentation
- [Docker Deployment](docs/deployment/docker.md) - Container deployment guide

## Quick Start

### Prerequisites

- Python 3.9 or higher (fully supports Python 3.13+)
- discord.py 2.4.0+ (required for Python 3.13 compatibility)
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Discord OAuth Application (for web interface login)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jkkicks/Vela.git
   cd Vela
   ```

2. **Set up a Python virtual environment**

   **Windows (PowerShell):**
   ```powershell
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   .\.venv\Scripts\Activate.ps1

   # If you get an execution policy error, run:
   # Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

   **Windows (Command Prompt):**
   ```cmd
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   .venv\Scripts\activate.bat
   ```

   **macOS/Linux:**
   ```bash
   # Create virtual environment
   python3 -m venv .venv

   # Activate virtual environment
   source .venv/bin/activate
   ```

   **To deactivate the virtual environment (all platforms):**
   ```bash
   deactivate
   ```

3. **Install dependencies** (with virtual environment activated)
   ```bash
   # IMPORTANT: Upgrade pip first (especially for Python 3.13+)
   python -m pip install --upgrade pip setuptools wheel
   pip cache purge

   # Install all dependencies
   pip install -r requirements.txt
   ```

4. **Download static assets**
   ```bash
   python download_assets.py
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Run the application**
   ```bash
   # Direct start:
   python -m src.main

   # Using startup script (handles venv, checks dependencies):
   python start.py

   # Restart (kills existing process on port 8000 first):
   python restart.py
   ```

7. **Complete initial setup**
   - Visit http://localhost:8000/setup
   - Enter your Discord bot token and admin credentials
   - Configure your first guild

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Database (SQLite or PostgreSQL)
DATABASE_URL=sqlite:///./vela.db
# DATABASE_URL=postgresql://user:password@localhost:5432/vela

# Discord Bot (optional - can be set via web UI)
BOT_TOKEN=your_bot_token_here
GUILD_ID=123456789012345678

# Discord OAuth (required for web login)
DISCORD_CLIENT_ID=your_app_client_id
DISCORD_CLIENT_SECRET=your_app_client_secret
DISCORD_REDIRECT_URI=http://localhost:8000/auth/callback

# Security
API_SECRET_KEY=change-this-secret-key
ENCRYPTION_KEY=generate-with-fernet

# API Settings
API_PORT=8000
API_HOST=0.0.0.0
```

### Discord OAuth Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create or select your application
3. Go to OAuth2 settings
4. Add redirect URL: `http://localhost:8000/auth/callback` (or your domain)
5. Copy Client ID and Client Secret to `.env`

## Deployment

### Docker Deployment

1. **Using Docker Compose (Recommended)**
   ```bash
   docker-compose up -d
   ```

2. **Using Docker directly**
   ```bash
   docker build -t vela .
   docker run -d -p 8000:8000 --env-file .env vela
   ```

**Note:** The Docker image includes tini as an init system for proper signal handling and graceful shutdowns. The container will properly handle SIGTERM signals for clean termination.

### Manual Deployment

1. **Install PostgreSQL** (optional, for production)
   ```bash
   sudo apt install postgresql
   ```

2. **Set up systemd service** (Linux)
   Create `/etc/systemd/system/vela.service`:
   ```ini
   [Unit]
   Description=Vela Discord Bot
   After=network.target

   [Service]
   Type=simple
   User=vela
   WorkingDirectory=/opt/vela
   ExecStart=/usr/bin/python3 -m src.main
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

3. **Start the service**
   ```bash
   sudo systemctl enable vela
   sudo systemctl start vela
   ```

## Usage

### Bot Commands

**Slash Commands:**
- `/onboard` - Complete onboarding process
- `/setnick` - Change your nickname
- `/help` - Display help information
- `/ping` - Check bot latency
- `/about` - Information about Vela
- `/server_info` - Server statistics

**Admin Commands:**
- `/remove @user` - Remove user from database
- `/stats` - View server statistics
- `/list_members` - List all members
- `/sync` - Sync slash commands

**Legacy Commands:**
- `!nick` - View current nickname
- `!setnick [firstname] [lastname]` - Change nickname
- `!reinit` - Re-initialize user in database
- `!99` - Get a Brooklyn Nine-Nine quote
- `!shutdown` - Shutdown the bot (owner only)

### Web Interface

Access the web interface at `http://localhost:8000`

**Available Pages:**
- `/` - Home page
- `/dashboard` - Statistics overview
- `/admin/users` - User management (with approve/demote onboarding controls)
- `/admin/config` - Bot configuration
- `/admin/logs` - Audit logs
- `/admin/guilds` - Multi-guild management (super admin only)
- `/apps/onboarding` - Onboarding workflow configuration
- `/apps/welcome` - Welcome message customization
- `/apps/notify` - Notification settings for Discord events
- `/apps/commands` - Command configuration

### API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Key API Endpoints (28+ total):**
- User Management: `GET/POST /users`, `GET/DELETE /users/{user_id}`
- Onboarding Control: `POST /users/{user_id}/approve`, `POST /users/{user_id}/demote`
- Guild Management: `GET /guilds`, `POST /settings/{guild_id}`
- Notifications: `POST /notifications/toggle`, `POST /notifications/channel`
- Data Export: `GET /export` (CSV/JSON formats)
- Commands: `GET/POST /commands/{guild_id}`

## Development

### Setting Up Development Environment

1. **Create and activate virtual environment:**

   **Windows PowerShell:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install development dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install --upgrade pip
   ```

3. **Verify installation:**
   ```bash
   python test_install.py
   ```

4. **IDE Configuration:**
   - **VS Code**: Select the interpreter from `.venv`
     - Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
     - Type "Python: Select Interpreter"
     - Choose `./.venv/Scripts/python.exe` (Windows) or `./.venv/bin/python` (Mac/Linux)

   - **PyCharm**: Configure project interpreter
     - Go to Settings → Project → Python Interpreter
     - Add interpreter → Existing environment
     - Select `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Mac/Linux)

### Project Structure

```
Vela/
├── src/
│   ├── bot/               # Discord bot implementation
│   │   ├── cogs/          # Command groups
│   │   └── views/         # UI components
│   ├── api/               # FastAPI web application
│   │   ├── routers/       # API endpoints
│   │   └── models/        # Pydantic schemas
│   └── shared/            # Shared database and config
├── templates/             # HTMX templates
│   ├── pages/            # Full pages
│   ├── fragments/        # HTMX fragments
│   └── components/       # Reusable components
├── static/               # Static assets
├── migrations/           # Database migrations
└── tests/               # Test suite
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

**Note:** `start.py` and `restart.py` are excluded from Black formatting to preserve critical signal handling code. These files contain specific formatting required for proper shutdown procedures.

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Architecture

### Technology Stack

- **Backend**: Python 3.9+ (including 3.13+)
- **Bot Framework**: discord.py 2.4.0+
- **Web Framework**: FastAPI
- **Database ORM**: SQLModel (Pydantic + SQLAlchemy)
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Authentication**: Discord OAuth2
- **Containerization**: Docker

### Design Principles

- **KISS**: Keep It Simple - Python-only stack, no build steps
- **DRY**: SQLModel for both API validation and database
- **Multi-guild Ready**: Architecture supports multiple Discord servers
- **Security First**: Encrypted tokens, OAuth authentication, audit logging
- **Progressive Enhancement**: HTMX for interactivity without JavaScript complexity
- **Graceful Operations**: Proper signal handling and shutdown procedures for both local and containerized environments
- **Modern Python**: Full support for Python 3.13+ with async/await patterns

## Migration from v1.0

If you're upgrading from the original Vela:

1. **Backup your data**
   ```bash
   cp member_data.db member_data.db.backup
   ```

2. **Run the new version**
   - The new version uses a different database structure
   - Existing data will NOT be automatically migrated
   - Use the web interface to re-configure your bot

## Contributing

Thank you for considering contributing to Vela! We welcome contributions from everyone.

1. Check [GitHub Issues](https://github.com/jkkicks/Vela/issues) for existing discussions
2. Fork the repository
3. Create a feature branch (`git checkout -b feature/amazing-feature`)
4. Make your changes following our code style
5. Write tests if applicable
6. Update documentation as needed
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

By contributing, you agree to license your contributions under the same license as the project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Virtual Environment Issues

**Windows PowerShell Execution Policy Error:**
```powershell
# If you see "cannot be loaded because running scripts is disabled"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again
.\.venv\Scripts\Activate.ps1
```

**Command Not Found (Mac/Linux):**
```bash
# Make sure python3 is installed
python3 --version

# If not installed:
# Mac: brew install python3
# Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip
```

**Wrong Python Version:**
```bash
# Check your Python version
python --version  # Windows
python3 --version # Mac/Linux

# Vela requires Python 3.9+
```

**Virtual Environment Not Activating:**
- Look for `(.venv)` at the beginning of your command prompt
- Windows: Try using Command Prompt instead of PowerShell
- Make sure you're in the Vela directory when activating

### Common Installation Issues

**Python 3.13 - ModuleNotFoundError: No module named 'audioop':**
```bash
# discord.py 2.3.2 doesn't support Python 3.13
# Upgrade to discord.py 2.4.0+
pip install --upgrade discord.py
```

**Dependency Conflicts:**
```bash
# Clean install in virtual environment
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Missing Static Assets:**
```bash
python download_assets.py
```

**Database Connection Issues:**
- SQLite: Ensure write permissions in current directory
- PostgreSQL: Check connection string in `.env`

## Support

- **Issues**: [GitHub Issues](https://github.com/jkkicks/Vela/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jkkicks/Vela/discussions)
- **Wiki**: [Documentation Wiki](https://github.com/jkkicks/Vela/wiki)

## Acknowledgments

- Discord.py community for the excellent bot framework
- FastAPI for the modern web framework
- HTMX for making web development fun again
- Original Vela contributors

---

Made with ❤️ by the Vela team