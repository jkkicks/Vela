"""Main FastAPI application"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from sqlmodel import Session, select

from src.shared.config import settings
from src.shared.database import init_database, get_session
from src.shared.models import AdminUser, Guild
from src.api.routers import auth, admin, htmx, api, setup
from src.api.routers.auth import get_current_user

logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Configure templates and static files
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    import asyncio
    import sys

    # Validate critical security settings before startup
    missing_configs = []

    if (
        not settings.api_secret_key
        or settings.api_secret_key == "change-this-secret-key-in-production"
    ):
        missing_configs.append("API_SECRET_KEY")

    if missing_configs:
        print("\n" + "=" * 80)
        print("STARTUP FAILED - MISSING REQUIRED CONFIGURATION")
        print("=" * 80)
        print("\nThe following required environment variables are not set:\n")
        for config in missing_configs:
            print(f"  [!] {config}")
        print("\n" + "-" * 80)
        print("How to fix:")
        print("-" * 80)
        print("\n1. Create a .env file in your project root with:")
        print("\n   API_SECRET_KEY=your-secure-random-secret-key-here")
        print("\n2. Or set environment variables when running Docker:")
        print("\n   docker run -e API_SECRET_KEY=your-secret-key ...")
        print("\n3. Generate a secure secret key:")
        print("\n   # Linux/Mac:")
        print("   openssl rand -base64 32")
        print("\n   # Python:")
        print("   python -c 'import secrets; print(secrets.token_urlsafe(32))'")
        print("\n" + "=" * 80)
        print("WARNING: Never use default values in production!")
        print("=" * 80 + "\n")

        logger.error("Application startup blocked due to missing configuration")
        sys.exit(1)

    # Startup
    print("\n" + "=" * 80)
    print("CONFIGURATION VALIDATED")
    print("=" * 80)
    print("\nLoaded Configuration:")
    print(f"  * API Host: {settings.api_host}:{settings.api_port}")
    print(f"  * Database: {settings.database_url}")
    print(f"  * API Secret Key: {'[OK]' if settings.api_secret_key and settings.api_secret_key != 'change-this-secret-key-in-production' else '[MISSING]'}")
    print(f"  * Encryption Key: {'[OK]' if settings.encryption_key else '[MISSING]'}")
    print(f"  * Discord Client ID: {'[OK]' if settings.discord_client_id else '[MISSING] (required for OAuth)'}")
    print(f"  * Discord Client Secret: {'[OK]' if settings.discord_client_secret else '[MISSING] (required for OAuth)'}")
    print(f"  * Bot Token: {'[OK]' if settings.bot_token else '[MISSING] (required for bot)'}")
    print(f"  * Debug Mode: {'Enabled' if settings.debug else 'Disabled'}")
    print(f"  * Log Level: {settings.log_level}")
    print("\n" + "=" * 80 + "\n")

    logger.info("Starting FastAPI application")
    init_database()

    try:
        yield
    except asyncio.CancelledError:
        # This is expected during shutdown, don't log as error
        logger.info("Application shutdown requested")
    finally:
        # Shutdown
        logger.info("Shutting down FastAPI application")


# Create FastAPI app
app = FastAPI(
    title="Vela Admin Panel",
    description="Web interface for managing Vela Discord bot",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add setup check middleware
@app.middleware("http")
async def setup_check_middleware(request: Request, call_next):
    """Redirect to setup if no admins exist, except for setup/auth routes"""
    # Skip middleware for static files, health check, and setup/auth routes
    if (
        request.url.path.startswith("/static")
        or request.url.path.startswith("/setup")
        or request.url.path.startswith("/auth")
        or request.url.path == "/health"
    ):
        return await call_next(request)

    # Check if admin exists
    from src.shared.database import SessionLocal

    with SessionLocal() as session:
        admin_exists = session.exec(select(AdminUser).limit(1)).first()

        if not admin_exists and request.url.path != "/setup":
            # No admin exists, redirect to setup
            return RedirectResponse(url="/setup", status_code=302)

    return await call_next(request)


# Mount static files
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")

# Include routers
app.include_router(setup.router, prefix="/setup", tags=["setup"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(htmx.router, prefix="/htmx", tags=["htmx"])
app.include_router(api.router, prefix="/api", tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = Depends(get_session)):
    """Home page - redirect to setup or dashboard"""
    # Check if any admin exists
    admin_exists = session.exec(select(AdminUser).limit(1)).first()

    if not admin_exists:
        # No admin exists, redirect to setup
        return RedirectResponse(url="/setup", status_code=302)

    # Admin exists, show login or dashboard
    # TODO: Check if user is logged in
    return templates.TemplateResponse(
        "pages/index.html", {"request": request, "title": "Vela Admin Panel"}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Dashboard page"""
    # Get statistics
    from src.shared.models import Member

    total_guilds = session.exec(select(Guild)).all()
    total_members = session.exec(select(Member)).all()
    onboarded_members = [m for m in total_members if m.onboarding_status > 0]

    # Get bot status (check if bot module is available)
    bot_info = None
    try:
        # Import bot instance from main if available
        from src.main import bot_instance

        if bot_instance and bot_instance.user:
            bot_info = {
                "online": True,
                "name": str(bot_instance.user),
                "id": bot_instance.user.id,
                "invite_url": f"https://discord.com/api/oauth2/authorize?client_id={bot_instance.user.id}&permissions=8&scope=bot%20applications.commands",
                "guilds": [
                    {"name": g.name, "id": g.id, "member_count": g.member_count}
                    for g in bot_instance.guilds
                ],
            }
    except (ImportError, AttributeError):
        # Bot not running or not available
        # Try to get client ID from settings for invite link
        from src.shared.config import settings

        if settings.discord_client_id:
            bot_info = {
                "online": False,
                "invite_url": f"https://discord.com/api/oauth2/authorize?client_id={settings.discord_client_id}&permissions=8&scope=bot%20applications.commands",
            }

    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            "request": request,
            "title": "Dashboard",
            "current_user": current_user,
            "stats": {
                "guilds": len(total_guilds),
                "members": len(total_members),
                "onboarded": len(onboarded_members),
                "pending": len(total_members) - len(onboarded_members),
            },
            "bot_info": bot_info,
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    """Custom 404 handler"""
    return templates.TemplateResponse(
        "pages/404.html",
        {"request": request, "title": "Page Not Found"},
        status_code=404,
    )


@app.exception_handler(500)
async def server_error(request: Request, exc: HTTPException):
    """Custom 500 handler"""
    return templates.TemplateResponse(
        "pages/500.html", {"request": request, "title": "Server Error"}, status_code=500
    )
