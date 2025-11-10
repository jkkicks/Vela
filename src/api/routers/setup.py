"""Setup router for first-run configuration"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timedelta
import logging
import secrets
import asyncio

from src.shared.database import get_session
from src.shared.models import AdminUser, Guild, Channel, Role
from src.shared.config import encrypt_value, settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

router = APIRouter()

# Store CSRF tokens for setup OAuth flow (in production, use Redis)
setup_csrf_tokens = {}

# Store temporary OAuth user data during setup (in production, use Redis with TTL)
setup_oauth_sessions = {}


async def start_discord_bot(request: Request, bot_token: str):
    """Start the Discord bot after initial setup"""
    try:
        # Check if bot is already running
        bot = getattr(request.app.state, "bot", None)
        if bot and bot.is_ready():
            logger.info("Bot is already running")
            return

        # Import bot-related modules
        from src.bot.main import VelaBot

        # Create and start the bot
        bot = VelaBot()
        request.app.state.bot = bot

        # Start the bot in the background
        asyncio.create_task(bot.start(bot_token))
        logger.info("Discord bot started successfully")

    except Exception as e:
        logger.error(f"Failed to start Discord bot: {e}")
        # Don't raise - allow the application to continue


def check_setup_allowed(session: Session):
    """Check if setup is allowed (no admins exist)"""
    admin_exists = session.exec(select(AdminUser).limit(1)).first()
    if admin_exists:
        raise HTTPException(403, "Setup already completed. Access denied.")


@router.get("/", response_class=HTMLResponse)
async def setup_page(request: Request, session: Session = Depends(get_session)):
    """Display setup page if no admins exist"""
    check_setup_allowed(session)

    # Check if user has completed OAuth (check for setup session cookie)
    setup_session_id = request.cookies.get("setup_session")
    discord_user = None

    if setup_session_id and setup_session_id in setup_oauth_sessions:
        discord_user = setup_oauth_sessions[setup_session_id]

    # Check if Discord OAuth is configured
    oauth_configured = bool(
        settings.discord_client_id and settings.discord_client_secret
    )

    # Pre-populate form fields from environment variables if available
    env_defaults = {
        "guild_id": settings.guild_id or "",
        "bot_token": settings.bot_token or "",
    }

    return templates.TemplateResponse(
        "pages/setup.html",
        {
            "request": request,
            "title": "Initial Setup",
            "discord_user": discord_user,
            "oauth_configured": oauth_configured,
            "env_defaults": env_defaults,
        },
    )


@router.get("/auth/discord")
async def setup_discord_login(session: Session = Depends(get_session)):
    """Initiate Discord OAuth flow for setup"""
    check_setup_allowed(session)

    if not settings.discord_client_id:
        raise HTTPException(500, "Discord OAuth not configured")

    # Generate CSRF token with "setup:" prefix to indicate this is for setup
    state = f"setup:{secrets.token_urlsafe(32)}"
    setup_csrf_tokens[state] = datetime.utcnow()

    # Clean old tokens (older than 10 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    tokens_copy = setup_csrf_tokens.copy()
    for token, timestamp in tokens_copy.items():
        if timestamp < cutoff:
            del setup_csrf_tokens[token]

    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,  # Use the same redirect URI as regular auth
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }

    discord_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(discord_url)


@router.post("/initialize")
async def initialize_setup(
    request: Request,
    guild_id: int = Form(...),
    guild_name: str = Form(...),
    bot_token: str = Form(...),
    welcome_channel_id: int = Form(None),
    onboarded_role_id: int = Form(None),
    onboarded_role_name: str = Form(None),
    session: Session = Depends(get_session),
):
    """Initialize the bot with first guild and admin"""
    # Double check no admins exist
    check_setup_allowed(session)

    # Verify user has authenticated via Discord OAuth
    setup_session_id = request.cookies.get("setup_session")
    if not setup_session_id or setup_session_id not in setup_oauth_sessions:
        raise HTTPException(
            403, "You must authenticate with Discord before completing setup"
        )

    discord_user = setup_oauth_sessions[setup_session_id]

    try:
        # Create first guild
        encrypted_token = encrypt_value(bot_token)
        guild = Guild(
            guild_id=guild_id,
            guild_name=guild_name,
            bot_token=encrypted_token,
            is_active=True,
        )
        session.add(guild)
        session.flush()  # Get the guild ID

        # Create super admin using OAuth data
        admin = AdminUser(
            discord_id=int(discord_user["discord_id"]),
            discord_username=discord_user["username"],
            guild_id=guild_id,
            is_super_admin=True,
        )
        session.add(admin)

        # Add welcome channel if provided
        if welcome_channel_id:
            channel = Channel(
                channel_id=welcome_channel_id,
                channel_type="welcome",
                guild_id=guild_id,
                name="welcome",
                enabled=True,
            )
            session.add(channel)

        # Add onboarded role if provided
        if onboarded_role_id and onboarded_role_name:
            role = Role(
                role_id=onboarded_role_id,
                role_name=onboarded_role_name,
                role_type="onboarded",
                guild_id=guild_id,
            )
            session.add(role)

        session.commit()

        # Clean up setup session
        if setup_session_id in setup_oauth_sessions:
            del setup_oauth_sessions[setup_session_id]

        logger.info(
            f"Setup completed. Guild: {guild_name}, Admin: {discord_user['username']}"
        )

        # Start the Discord bot now that setup is complete
        asyncio.create_task(start_discord_bot(request, bot_token))
        logger.info("Discord bot startup initiated")

        # Redirect to login
        redirect = RedirectResponse(url="/auth/login", status_code=302)
        redirect.delete_cookie("setup_session")
        return redirect

    except Exception as e:
        logger.error(f"Setup error: {e}")
        session.rollback()
        raise HTTPException(500, f"Setup failed: {str(e)}")


@router.get("/check")
async def check_setup(session: Session = Depends(get_session)):
    """Check if setup is required"""
    admin_exists = session.exec(select(AdminUser).limit(1)).first()
    return {"setup_required": not admin_exists}
