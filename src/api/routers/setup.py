"""Setup router for first-run configuration"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
import logging

from src.shared.database import get_session
from src.shared.models import AdminUser, Guild, Channel, Role
from src.shared.config import encrypt_value

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

router = APIRouter()


def check_setup_allowed(session: Session):
    """Check if setup is allowed (no admins exist)"""
    admin_exists = session.exec(select(AdminUser).limit(1)).first()
    if admin_exists:
        raise HTTPException(403, "Setup already completed. Access denied.")


@router.get("/", response_class=HTMLResponse)
async def setup_page(
    request: Request,
    session: Session = Depends(get_session)
):
    """Display setup page if no admins exist"""
    check_setup_allowed(session)

    return templates.TemplateResponse("pages/setup.html", {
        "request": request,
        "title": "Initial Setup"
    })


@router.post("/initialize")
async def initialize_setup(
    guild_id: int = Form(...),
    guild_name: str = Form(...),
    bot_token: str = Form(...),
    discord_admin_id: int = Form(...),
    discord_username: str = Form(...),
    welcome_channel_id: int = Form(None),
    onboarded_role_id: int = Form(None),
    onboarded_role_name: str = Form(None),
    session: Session = Depends(get_session)
):
    """Initialize the bot with first guild and admin"""
    # Double check no admins exist
    check_setup_allowed(session)

    try:
        # Create first guild
        encrypted_token = encrypt_value(bot_token)
        guild = Guild(
            guild_id=guild_id,
            guild_name=guild_name,
            bot_token=encrypted_token,
            is_active=True
        )
        session.add(guild)
        session.flush()  # Get the guild ID

        # Create super admin
        admin = AdminUser(
            discord_id=discord_admin_id,
            discord_username=discord_username,
            guild_id=guild_id,
            is_super_admin=True
        )
        session.add(admin)

        # Add welcome channel if provided
        if welcome_channel_id:
            channel = Channel(
                channel_id=welcome_channel_id,
                channel_type="welcome",
                guild_id=guild_id,
                name="welcome",
                enabled=True
            )
            session.add(channel)

        # Add onboarded role if provided
        if onboarded_role_id and onboarded_role_name:
            role = Role(
                role_id=onboarded_role_id,
                role_name=onboarded_role_name,
                role_type="onboarded",
                guild_id=guild_id
            )
            session.add(role)

        session.commit()

        logger.info(f"Setup completed. Guild: {guild_name}, Admin: {discord_username}")

        # Redirect to login
        return RedirectResponse(url="/auth/login", status_code=302)

    except Exception as e:
        logger.error(f"Setup error: {e}")
        session.rollback()
        raise HTTPException(500, f"Setup failed: {str(e)}")


@router.get("/check")
async def check_setup(session: Session = Depends(get_session)):
    """Check if setup is required"""
    admin_exists = session.exec(select(AdminUser).limit(1)).first()
    return {"setup_required": not admin_exists}