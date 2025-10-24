"""Admin router for web interface pages"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
import logging

from src.shared.database import get_session
from src.shared.models import Member, Guild, Channel, Role, Config, AuditLog
from src.api.routers.auth import get_current_user

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

router = APIRouter()


@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Users management page"""
    # Get users based on admin permissions
    if current_user['is_super_admin']:
        members = session.exec(select(Member)).all()
    else:
        members = session.exec(
            select(Member).where(Member.guild_id == current_user['guild_id'])
        ).all()

    return templates.TemplateResponse("pages/users.html", {
        "request": request,
        "title": "User Management",
        "users": members,
        "current_user": current_user
    })


@router.get("/config", response_class=HTMLResponse)
async def config_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user['guild_id'])
    ).first()

    configs = session.exec(
        select(Config).where(Config.guild_id == current_user['guild_id'])
    ).all()

    channels = session.exec(
        select(Channel).where(Channel.guild_id == current_user['guild_id'])
    ).all()

    roles = session.exec(
        select(Role).where(Role.guild_id == current_user['guild_id'])
    ).all()

    return templates.TemplateResponse("pages/config.html", {
        "request": request,
        "title": "Configuration",
        "guild": guild,
        "configs": configs,
        "channels": channels,
        "roles": roles,
        "current_user": current_user
    })


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Audit logs page"""
    # Get audit logs
    if current_user['is_super_admin']:
        logs = session.exec(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
        ).all()
    else:
        logs = session.exec(
            select(AuditLog)
            .where(AuditLog.guild_id == current_user['guild_id'])
            .order_by(AuditLog.timestamp.desc())
            .limit(100)
        ).all()

    return templates.TemplateResponse("pages/logs.html", {
        "request": request,
        "title": "Audit Logs",
        "logs": logs,
        "current_user": current_user
    })


@router.get("/guilds", response_class=HTMLResponse)
async def guilds_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Guilds management page (super admin only)"""
    if not current_user['is_super_admin']:
        raise HTTPException(403, "Access denied")

    guilds = session.exec(select(Guild)).all()

    return templates.TemplateResponse("pages/guilds.html", {
        "request": request,
        "title": "Guild Management",
        "guilds": guilds,
        "current_user": current_user
    })