# Project Structure

Understanding the SparkBot codebase organization.

## Directory Overview

```
SparkBot/
├── src/                        # Source code
│   ├── bot/                   # Discord bot implementation
│   │   ├── main.py           # Bot entry point and core logic
│   │   ├── cogs/             # Command groups (modular features)
│   │   │   ├── onboarding.py # Onboarding commands and logic
│   │   │   ├── admin.py      # Admin-only commands
│   │   │   └── utilities.py  # Utility and fun commands
│   │   └── views/            # Discord UI components
│   │       └── onboarding.py # Buttons and modals for onboarding
│   │
│   ├── api/                   # FastAPI web application
│   │   ├── main.py           # FastAPI app initialization
│   │   ├── routers/          # API endpoint groups
│   │   │   ├── auth.py       # Discord OAuth authentication
│   │   │   ├── admin.py      # Admin panel page routes
│   │   │   ├── htmx.py       # HTMX fragment endpoints
│   │   │   ├── api.py        # REST API endpoints
│   │   │   └── setup.py      # First-run setup wizard
│   │   └── models/           # Data models
│   │       └── schemas.py    # Pydantic schemas for API
│   │
│   ├── shared/                # Shared between bot and API
│   │   ├── database.py       # Database connection and session
│   │   ├── models.py         # SQLModel database models
│   │   └── config.py         # Configuration management
│   │
│   └── main.py               # Main entry point (runs both bot and API)
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html             # Base template with common elements
│   ├── pages/                # Full page templates
│   │   ├── dashboard.html    # Main dashboard
│   │   ├── users.html        # User management
│   │   ├── config.html       # Configuration page
│   │   └── setup.html        # First-run setup
│   ├── fragments/            # HTMX partial templates
│   │   ├── user_table.html  # Dynamic user table
│   │   └── user_row.html    # Individual user row
│   └── components/           # Reusable UI components
│       ├── navbar.html       # Navigation bar
│       └── sidebar.html      # Side navigation
│
├── static/                    # Static assets
│   ├── htmx.min.js          # HTMX library (downloaded)
│   ├── alpine.min.js        # Alpine.js library (downloaded)
│   └── custom.css           # Custom styles
│
├── migrations/               # Database migrations (Alembic)
│   ├── env.py               # Migration environment config
│   ├── script.py.mako       # Migration template
│   └── versions/            # Migration files
│
├── docs/                     # Documentation
│   ├── README.md            # Documentation index
│   ├── guides/              # How-to guides
│   ├── development/         # Development docs
│   ├── deployment/          # Deployment guides
│   └── api/                 # API reference
│
├── tests/                    # Test suite
│   ├── test_bot/            # Bot tests
│   ├── test_api/            # API tests
│   └── test_shared/         # Shared module tests
│
├── planning/                 # Project planning (gitignored)
│   └── planning.md          # Implementation plan
│
├── .env.example             # Environment variables template
├── .env                     # Local environment variables (gitignored)
├── .gitignore              # Git ignore patterns
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Docker Compose configuration
├── alembic.ini            # Alembic configuration
├── README.md              # Main project README
├── LICENSE                # Project license
├── CONTRIBUTING.md        # Contribution guidelines
├── start.py               # Quick start script
├── download_assets.py     # Download static assets
└── test_install.py        # Installation verification
```

## Key Modules Explained

### src/bot/
The Discord bot implementation using discord.py.

**main.py**: Core bot class (`SparkBot`) that:
- Initializes the bot with intents
- Loads cogs (command modules)
- Handles events (on_ready, on_member_join, etc.)
- Sets up persistent views

**cogs/**: Modular command groups for organization:
- Each cog is a class that groups related commands
- Can be loaded/unloaded independently
- Easier to maintain and test

**views/**: Discord UI components:
- Persistent buttons that survive bot restarts
- Modal forms for data collection
- Custom interaction handlers

### src/api/
The web interface using FastAPI.

**main.py**: FastAPI application that:
- Sets up routes and middleware
- Configures CORS and static files
- Handles lifespan events
- Mounts routers

**routers/**: Endpoint groups:
- `auth.py`: Discord OAuth flow
- `admin.py`: Full page routes
- `htmx.py`: Partial HTML responses
- `api.py`: JSON REST endpoints
- `setup.py`: First-run configuration

**models/**: Data schemas:
- Pydantic models for request/response validation
- Separate from database models for flexibility

### src/shared/
Code shared between bot and web interface.

**database.py**: Database management:
- Engine configuration
- Session factory
- Support for SQLite and PostgreSQL
- Database initialization

**models.py**: SQLModel definitions:
- Single source of truth for data structure
- Used by both bot and API
- Includes relationships and validations

**config.py**: Configuration management:
- Environment variable loading
- Settings validation
- Encryption/decryption utilities
- Dynamic configuration from database

### Templates (HTMX Architecture)

**pages/**: Complete HTML pages
- Full document structure
- Include base template
- Load HTMX for interactivity

**fragments/**: Partial HTML snippets
- Returned by HTMX endpoints
- Dynamically update page sections
- No full page reload needed

**components/**: Reusable UI parts
- Navigation elements
- Common UI patterns
- Included in multiple pages

## Data Flow

### Bot Command Flow
1. User types command in Discord
2. Discord.py receives interaction
3. Routes to appropriate cog
4. Cog method processes command
5. Accesses database via shared models
6. Returns response to Discord

### Web Request Flow
1. User visits web interface
2. FastAPI receives request
3. Routes to appropriate handler
4. Handler queries database
5. Renders template with data
6. Returns HTML response

### HTMX Request Flow
1. User interacts with page element
2. HTMX sends background request
3. Server returns HTML fragment
4. HTMX updates page section
5. No full page reload

## Key Design Patterns

### Separation of Concerns
- Bot logic separate from web logic
- Shared database layer
- Independent deployment possible

### Modular Architecture
- Cogs for bot features
- Routers for API endpoints
- Reusable templates

### Configuration Management
- Environment variables for secrets
- Database for runtime config
- Encryption for sensitive data

### Progressive Enhancement
- HTMX for dynamic features
- Works without JavaScript
- Server-side rendering

## Development Workflow

### Adding a Bot Command
1. Create/edit cog in `src/bot/cogs/`
2. Define command method with decorators
3. Implement logic
4. Bot auto-loads on restart

### Adding a Web Page
1. Create router in `src/api/routers/`
2. Create template in `templates/pages/`
3. Define endpoint in router
4. Include router in main app

### Adding Database Model
1. Define model in `src/shared/models.py`
2. Create migration: `alembic revision --autogenerate`
3. Apply migration: `alembic upgrade head`
4. Use in bot/API code

### Adding HTMX Feature
1. Create fragment template
2. Add HTMX attributes to trigger element
3. Create endpoint returning fragment
4. Server returns partial HTML

## Best Practices

### Code Organization
- Keep related code together
- Use descriptive names
- Follow Python conventions
- Add docstrings

### Database Access
- Use context managers for sessions
- Handle exceptions properly
- Use SQLModel relationships
- Validate data with Pydantic

### Security
- Never hardcode secrets
- Validate all inputs
- Use prepared statements
- Implement proper auth

### Testing
- Unit test individual functions
- Integration test API endpoints
- Test bot commands
- Mock external services

## Next Steps

- [Setting Up Development Environment](setup.md)
- [Understanding Virtual Environments](virtual-environments.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)
- [API Reference](../api/web-api.md)