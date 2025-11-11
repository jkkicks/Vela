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
    current_user=Depends(get_current_user),
):
    """Users management page"""
    # Get users based on admin permissions
    if current_user["is_super_admin"]:
        members = session.exec(select(Member)).all()
    else:
        members = session.exec(
            select(Member).where(Member.guild_id == current_user["guild_id"])
        ).all()

    return templates.TemplateResponse(
        "pages/users.html",
        {
            "request": request,
            "title": "User Management",
            "users": members,
            "current_user": current_user,
        },
    )


@router.get("/config", response_class=HTMLResponse)
async def config_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    configs = session.exec(
        select(Config).where(Config.guild_id == current_user["guild_id"])
    ).all()

    channels = session.exec(
        select(Channel).where(Channel.guild_id == current_user["guild_id"])
    ).all()

    roles = session.exec(
        select(Role).where(Role.guild_id == current_user["guild_id"])
    ).all()

    return templates.TemplateResponse(
        "pages/config.html",
        {
            "request": request,
            "title": "Configuration",
            "guild": guild,
            "configs": configs,
            "channels": channels,
            "roles": roles,
            "current_user": current_user,
        },
    )


@router.get("/apps", response_class=HTMLResponse)
async def apps_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Apps management page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    # Get app configurations from guild settings
    apps = {}
    if guild and guild.settings:
        apps = {
            "welcome_system": {"enabled": guild.settings.get("welcome_enabled", False)},
            "onboarding": {"enabled": guild.settings.get("onboarding_enabled", False)},
            "member_management": {
                "enabled": guild.settings.get("member_management_enabled", False)
            },
            "member_support": {
                "enabled": guild.settings.get("member_support_enabled", False)
            },
            "notifications": {
                "enabled": guild.settings.get("notifications_enabled", False)
            },
        }
    else:
        # Default values if no guild settings exist
        apps = {
            "welcome_system": {"enabled": False},
            "onboarding": {"enabled": False},
            "member_management": {"enabled": False},
            "member_support": {"enabled": False},
            "notifications": {"enabled": False},
        }

    return templates.TemplateResponse(
        "pages/apps.html",
        {
            "request": request,
            "title": "Apps",
            "guild": guild,
            "apps": apps,
            "current_user": current_user,
        },
    )


@router.get("/apps/welcome", response_class=HTMLResponse)
async def welcome_app_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Welcome System app configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    # Get welcome channel
    welcome_channel = session.exec(
        select(Channel).where(
            Channel.guild_id == current_user["guild_id"],
            Channel.channel_type == "welcome",
        )
    ).first()

    return templates.TemplateResponse(
        "pages/apps/welcome.html",
        {
            "request": request,
            "title": "Welcome System Configuration",
            "guild": guild,
            "welcome_channel": welcome_channel,
            "current_user": current_user,
        },
    )


@router.get("/apps/support", response_class=HTMLResponse)
async def support_app_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Member Support app configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    return templates.TemplateResponse(
        "pages/apps/support.html",
        {
            "request": request,
            "title": "Member Support Configuration",
            "guild": guild,
            "current_user": current_user,
        },
    )


@router.get("/apps/onboarding", response_class=HTMLResponse)
async def onboarding_app_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Onboarding app configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    # Get onboarded role
    onboarded_role = session.exec(
        select(Role).where(
            Role.guild_id == current_user["guild_id"], Role.role_type == "onboarded"
        )
    ).first()

    # Get approval channel
    approval_channel = session.exec(
        select(Channel).where(
            Channel.guild_id == current_user["guild_id"],
            Channel.channel_type == "onboarding_approval",
        )
    ).first()

    # Get approver roles
    approver_roles = session.exec(
        select(Role).where(
            Role.guild_id == current_user["guild_id"],
            Role.role_type == "onboarding_approver",
        )
    ).all()

    return templates.TemplateResponse(
        "pages/apps/onboarding.html",
        {
            "request": request,
            "title": "Onboarding Configuration",
            "guild": guild,
            "onboarded_role": onboarded_role,
            "approval_channel": approval_channel,
            "approver_roles": approver_roles,
            "current_user": current_user,
        },
    )


@router.get("/apps/commands", response_class=HTMLResponse)
async def commands_app_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Slash Commands app configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    # Get all roles for this guild
    roles = session.exec(
        select(Role).where(Role.guild_id == current_user["guild_id"])
    ).all()

    return templates.TemplateResponse(
        "pages/apps/commands.html",
        {
            "request": request,
            "title": "Slash Commands Configuration",
            "guild": guild,
            "roles": roles,
            "current_user": current_user,
        },
    )


@router.get("/apps/notify", response_class=HTMLResponse)
async def notify_app_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Notifications app configuration page"""
    # Get guild configuration
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    # Get notification channels
    member_join_channel = session.exec(
        select(Channel).where(
            Channel.guild_id == current_user["guild_id"],
            Channel.channel_type == "notification_member_join",
        )
    ).first()

    onboarding_complete_channel = session.exec(
        select(Channel).where(
            Channel.guild_id == current_user["guild_id"],
            Channel.channel_type == "notification_onboarding_complete",
        )
    ).first()

    return templates.TemplateResponse(
        "pages/apps/notify.html",
        {
            "request": request,
            "title": "Notifications Configuration",
            "guild": guild,
            "member_join_channel": member_join_channel,
            "onboarding_complete_channel": onboarding_complete_channel,
            "current_user": current_user,
        },
    )


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Audit logs page"""
    # Get audit logs
    if current_user["is_super_admin"]:
        logs = session.exec(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
        ).all()
    else:
        logs = session.exec(
            select(AuditLog)
            .where(AuditLog.guild_id == current_user["guild_id"])
            .order_by(AuditLog.timestamp.desc())
            .limit(100)
        ).all()

    return templates.TemplateResponse(
        "pages/logs.html",
        {
            "request": request,
            "title": "Audit Logs",
            "logs": logs,
            "current_user": current_user,
        },
    )


@router.get("/guilds", response_class=HTMLResponse)
async def guilds_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Guilds management page (super admin only)"""
    if not current_user["is_super_admin"]:
        raise HTTPException(403, "Access denied")

    guilds = session.exec(select(Guild)).all()

    return templates.TemplateResponse(
        "pages/guilds.html",
        {
            "request": request,
            "title": "Guild Management",
            "guilds": guilds,
            "current_user": current_user,
        },
    )
