"""HTMX router for dynamic HTML fragment updates"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from datetime import datetime
import logging

from src.shared.database import get_session
from src.shared.models import Member, Config, AuditLog
from src.api.routers.auth import get_current_user

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

router = APIRouter()


@router.get("/users/search", response_class=HTMLResponse)
async def search_users(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Search users and return table fragment"""
    query = select(Member)

    # Filter by guild if not super admin
    if not current_user["is_super_admin"]:
        query = query.where(Member.guild_id == current_user["guild_id"])

    # Search filter
    if q:
        query = query.where(
            (Member.username.contains(q))
            | (Member.nickname.contains(q))
            | (Member.firstname.contains(q))
            | (Member.lastname.contains(q))
        )

    users = session.exec(query).all()

    return templates.TemplateResponse(
        "fragments/user_table.html", {"request": request, "users": users}
    )


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(
    request: Request,
    user_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Return edit form for user"""
    user = session.exec(select(Member).where(Member.id == user_id)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user["is_super_admin"] and user.guild_id != current_user["guild_id"]:
        raise HTTPException(403, "Access denied")

    return templates.TemplateResponse(
        "fragments/user_edit_form.html", {"request": request, "user": user}
    )


@router.put("/users/{user_id}", response_class=HTMLResponse)
async def update_user(
    request: Request,
    user_id: int,
    firstname: str = Form(...),
    lastname: str = Form(...),
    email: str = Form(None),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update user and return updated row"""
    user = session.exec(select(Member).where(Member.id == user_id)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user["is_super_admin"] and user.guild_id != current_user["guild_id"]:
        raise HTTPException(403, "Access denied")

    # Update user
    user.firstname = firstname
    user.lastname = lastname
    user.email = email
    user.nickname = f"{firstname} {lastname}"
    user.last_change_datetime = datetime.utcnow()

    session.commit()

    # Log the action
    audit_log = AuditLog(
        guild_id=user.guild_id,
        user_id=user.user_id,
        discord_username=current_user["username"],
        action="user_updated",
        details={
            "updated_by": current_user["username"],
            "changes": {"firstname": firstname, "lastname": lastname, "email": email},
        },
    )
    session.add(audit_log)
    session.commit()

    return templates.TemplateResponse(
        "fragments/user_row.html", {"request": request, "user": user}
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Delete user and return empty response for row removal"""
    user = session.exec(select(Member).where(Member.id == user_id)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user["is_super_admin"] and user.guild_id != current_user["guild_id"]:
        raise HTTPException(403, "Access denied")

    # Log before deletion
    audit_log = AuditLog(
        guild_id=user.guild_id,
        user_id=user.user_id,
        discord_username=current_user["username"],
        action="user_deleted",
        details={
            "deleted_by": current_user["username"],
            "user_data": {"username": user.username, "nickname": user.nickname},
        },
    )
    session.add(audit_log)

    # Delete user
    session.delete(user)
    session.commit()

    return ""  # Return empty string for HTMX to remove the row


@router.post("/users/{user_id}/reset-onboarding")
async def reset_onboarding(
    user_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Reset user's onboarding status"""
    user = session.exec(select(Member).where(Member.id == user_id)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user["is_super_admin"] and user.guild_id != current_user["guild_id"]:
        raise HTTPException(403, "Access denied")

    # Reset onboarding
    user.onboarding_status = 0
    user.onboarding_completed_at = None
    user.nickname = None
    user.firstname = None
    user.lastname = None
    session.commit()

    # Log the action
    audit_log = AuditLog(
        guild_id=user.guild_id,
        user_id=user.user_id,
        discord_username=current_user["username"],
        action="onboarding_reset",
        details={"reset_by": current_user["username"]},
    )
    session.add(audit_log)
    session.commit()

    return {"status": "success", "message": "Onboarding reset successfully"}


@router.get("/config/{key}/edit", response_class=HTMLResponse)
async def edit_config_form(
    request: Request,
    key: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Return edit form for configuration"""
    config = session.exec(
        select(Config).where(
            Config.key == key, Config.guild_id == current_user["guild_id"]
        )
    ).first()

    return templates.TemplateResponse(
        "fragments/config_form.html", {"request": request, "config": config, "key": key}
    )


@router.post("/config/{key}")
async def update_config(
    key: str,
    value: str = Form(...),
    description: str = Form(None),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update configuration value"""
    config = session.exec(
        select(Config).where(
            Config.key == key, Config.guild_id == current_user["guild_id"]
        )
    ).first()

    if config:
        config.value = value
        if description:
            config.description = description
        config.updated_at = datetime.utcnow()
    else:
        config = Config(
            key=key,
            value=value,
            guild_id=current_user["guild_id"],
            description=description,
        )
        session.add(config)

    session.commit()

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        discord_username=current_user["username"],
        action="config_updated",
        details={"key": key, "value": value, "updated_by": current_user["username"]},
    )
    session.add(audit_log)
    session.commit()

    return {"status": "success", "message": f"Configuration '{key}' updated"}


@router.get("/logs/stream", response_class=HTMLResponse)
async def stream_logs(
    request: Request,
    last_id: int = 0,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Stream new log entries"""
    query = select(AuditLog).where(AuditLog.id > last_id)

    if not current_user["is_super_admin"]:
        query = query.where(AuditLog.guild_id == current_user["guild_id"])

    logs = session.exec(query.order_by(AuditLog.timestamp.desc()).limit(10)).all()

    return templates.TemplateResponse(
        "fragments/log_entries.html", {"request": request, "logs": logs}
    )
