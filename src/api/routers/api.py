"""REST API router for JSON endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import logging

from src.shared.database import get_session
from src.shared.models import Member, Guild, Config, AuditLog, Role
from src.api.routers.auth import get_current_user
from src.api.models.schemas import (
    MemberResponse,
    GuildResponse,
    ConfigResponse,
    StatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get server statistics"""
    if current_user['is_super_admin']:
        total_guilds = session.exec(select(Guild)).all()
        total_members = session.exec(select(Member)).all()
    else:
        total_guilds = session.exec(
            select(Guild).where(Guild.guild_id == current_user['guild_id'])
        ).all()
        total_members = session.exec(
            select(Member).where(Member.guild_id == current_user['guild_id'])
        ).all()

    onboarded = [m for m in total_members if m.onboarding_status > 0]

    return StatsResponse(
        total_guilds=len(total_guilds),
        total_members=len(total_members),
        onboarded_members=len(onboarded),
        pending_members=len(total_members) - len(onboarded)
    )


@router.get("/users", response_model=List[MemberResponse])
async def get_users(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    onboarded_only: bool = False,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get list of users"""
    query = select(Member)

    # Filter by guild if not super admin
    if not current_user['is_super_admin']:
        query = query.where(Member.guild_id == current_user['guild_id'])

    # Search filter
    if search:
        query = query.where(
            (Member.username.contains(search)) |
            (Member.nickname.contains(search)) |
            (Member.firstname.contains(search)) |
            (Member.lastname.contains(search))
        )

    # Onboarding filter
    if onboarded_only:
        query = query.where(Member.onboarding_status > 0)

    # Apply pagination
    query = query.offset(offset).limit(limit)

    members = session.exec(query).all()

    return [MemberResponse.from_orm(m) for m in members]


@router.get("/users/{user_id}", response_model=MemberResponse)
async def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get single user details"""
    user = session.exec(
        select(Member).where(Member.id == user_id)
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user['is_super_admin'] and user.guild_id != current_user['guild_id']:
        raise HTTPException(403, "Access denied")

    return MemberResponse.from_orm(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Delete a user from the database and reset their Discord nickname"""
    user = session.exec(
        select(Member).where(Member.id == user_id)
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user['is_super_admin'] and user.guild_id != current_user['guild_id']:
        raise HTTPException(403, "Access denied")

    # Reset Discord nickname and remove role (before deleting from DB)
    discord_updated = False
    try:
        # Access bot instance from FastAPI app state
        bot_instance = getattr(request.app.state, 'bot', None)
        logger.info(f"Attempting to reset Discord state for {user.username} (ID: {user.user_id}, Guild: {user.guild_id})")

        if bot_instance and bot_instance.user:
            logger.info(f"Bot instance found: {bot_instance.user.name}")
            guild = bot_instance.get_guild(user.guild_id)

            if guild:
                logger.info(f"Guild found: {guild.name} (ID: {guild.id})")
                member = guild.get_member(user.user_id)

                if member:
                    logger.info(f"Member found: {member.name} (current nick: {member.nick})")
                    # Reset nickname
                    try:
                        await member.edit(nick=None)
                        logger.info(f"✓ Reset nickname for {user.username}")
                        discord_updated = True
                    except Exception as e:
                        logger.warning(f"Could not reset nickname for {user.username}: {e}")

                    # Remove onboarded role
                    try:
                        onboarded_role = session.exec(
                            select(Role).where(
                                Role.guild_id == user.guild_id,
                                Role.role_type == "onboarded"
                            )
                        ).first()
                        if onboarded_role:
                            role = guild.get_role(onboarded_role.role_id)
                            if role and role in member.roles:
                                await member.remove_roles(role)
                                logger.info(f"✓ Removed onboarded role from {user.username}")
                        else:
                            logger.info(f"No onboarded role configured for guild {user.guild_id}")
                    except Exception as e:
                        logger.warning(f"Could not remove role from {user.username}: {e}")
                else:
                    logger.warning(f"✗ Member {user.user_id} not found in guild {user.guild_id}")
            else:
                logger.warning(f"✗ Guild {user.guild_id} not found. Bot is in guilds: {[g.id for g in bot_instance.guilds]}")
        else:
            logger.warning(f"✗ Bot instance not ready (instance: {bot_instance}, has user: {bot_instance.user if bot_instance else 'N/A'})")
    except ImportError:
        logger.warning("✗ Bot instance not available, cannot reset Discord nickname")
    except Exception as e:
        logger.error(f"✗ Error resetting Discord state for {user.username}: {e}")

    # Log the deletion
    audit_log = AuditLog(
        guild_id=user.guild_id,
        user_id=current_user['discord_id'],
        discord_username=current_user['username'],
        action="user_deleted",
        details={
            "deleted_user_id": user.user_id,
            "deleted_username": user.username,
            "deleted_by": current_user['username'],
            "discord_updated": discord_updated
        }
    )
    session.add(audit_log)

    # Delete the user
    session.delete(user)
    session.commit()

    logger.info(f"User {user.username} (ID: {user.user_id}) deleted by {current_user['username']}")

    return {
        "message": "User deleted successfully",
        "user_id": user_id,
        "discord_updated": discord_updated
    }


@router.get("/guilds", response_model=List[GuildResponse])
async def get_guilds(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get list of guilds (super admin only)"""
    if not current_user['is_super_admin']:
        # Regular admin only sees their guild
        guilds = session.exec(
            select(Guild).where(Guild.guild_id == current_user['guild_id'])
        ).all()
    else:
        guilds = session.exec(select(Guild)).all()

    return [GuildResponse.from_orm(g) for g in guilds]


@router.get("/config", response_model=List[ConfigResponse])
async def get_configs(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Get all configuration values"""
    configs = session.exec(
        select(Config).where(Config.guild_id == current_user['guild_id'])
    ).all()

    return [ConfigResponse.from_orm(c) for c in configs]


@router.get("/users/export")
async def export_users(
    format: str = Query("csv", regex="^(csv|json)$"),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Export users data"""
    query = select(Member)

    if not current_user['is_super_admin']:
        query = query.where(Member.guild_id == current_user['guild_id'])

    members = session.exec(query).all()

    if format == "json":
        return [
            {
                "user_id": m.user_id,
                "username": m.username,
                "nickname": m.nickname,
                "firstname": m.firstname,
                "lastname": m.lastname,
                "email": m.email,
                "onboarding_status": m.onboarding_status,
                "join_date": m.join_datetime.isoformat() if m.join_datetime else None
            }
            for m in members
        ]
    else:
        # CSV format
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "User ID", "Username", "Nickname", "First Name", "Last Name",
            "Email", "Onboarding Status", "Join Date"
        ])

        # Data
        for m in members:
            writer.writerow([
                m.user_id, m.username, m.nickname, m.firstname, m.lastname,
                m.email, m.onboarding_status,
                m.join_datetime.isoformat() if m.join_datetime else ""
            ])

        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )


@router.post("/config/channel")
async def configure_channel(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Configure a channel for the guild"""
    data = await request.json()
    channel_id = data.get('channel_id')
    channel_type = data.get('channel_type')
    name = data.get('name')

    if not channel_id or not channel_type:
        raise HTTPException(400, "channel_id and channel_type are required")

    # Check if channel already exists
    existing_channel = session.exec(
        select(Channel).where(
            Channel.guild_id == current_user['guild_id'],
            Channel.channel_type == channel_type
        )
    ).first()

    if existing_channel:
        # Update existing channel
        existing_channel.channel_id = channel_id
        if name:
            existing_channel.name = name
        existing_channel.enabled = True
    else:
        # Create new channel
        channel = Channel(
            channel_id=channel_id,
            channel_type=channel_type,
            guild_id=current_user['guild_id'],
            name=name,
            enabled=True
        )
        session.add(channel)

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user['guild_id'],
        user_id=current_user['discord_id'],
        discord_username=current_user['username'],
        action="channel_configured",
        details={
            "channel_id": channel_id,
            "channel_type": channel_type,
            "name": name
        }
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Channel {channel_type} configured by {current_user['username']}")

    return {"message": "Channel configured successfully"}


@router.post("/config/role")
async def configure_role(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Configure a role for the guild"""
    data = await request.json()
    role_id = data.get('role_id')
    role_type = data.get('role_type')
    role_name = data.get('role_name')

    if not role_id or not role_type or not role_name:
        raise HTTPException(400, "role_id, role_type, and role_name are required")

    # Check if role already exists
    existing_role = session.exec(
        select(Role).where(
            Role.guild_id == current_user['guild_id'],
            Role.role_type == role_type
        )
    ).first()

    if existing_role:
        # Update existing role
        existing_role.role_id = role_id
        existing_role.role_name = role_name
    else:
        # Create new role
        role = Role(
            role_id=role_id,
            role_name=role_name,
            role_type=role_type,
            guild_id=current_user['guild_id']
        )
        session.add(role)

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user['guild_id'],
        user_id=current_user['discord_id'],
        discord_username=current_user['username'],
        action="role_configured",
        details={
            "role_id": role_id,
            "role_type": role_type,
            "role_name": role_name
        }
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Role {role_type} configured by {current_user['username']}")

    return {"message": "Role configured successfully"}


@router.post("/config/setting")
async def update_setting(
    request: Request,
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Update a guild setting"""
    data = await request.json()
    key = data.get('key')
    value = data.get('value')

    if not key:
        raise HTTPException(400, "key is required")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user['guild_id'])
    ).first()

    if not guild:
        raise HTTPException(404, "Guild not found")

    # Update settings
    if guild.settings is None:
        guild.settings = {}

    guild.settings[key] = value

    # Force SQLAlchemy to detect the change
    from sqlalchemy.orm import attributes
    attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user['guild_id'],
        user_id=current_user['discord_id'],
        discord_username=current_user['username'],
        action="setting_updated",
        details={
            "key": key,
            "value": value
        }
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Setting {key} updated to {value} by {current_user['username']}")

    return {"message": "Setting updated successfully"}


@router.post("/config/reset")
async def reset_configuration(
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """Reset all configuration for the guild"""
    # Delete all channels
    channels = session.exec(
        select(Channel).where(Channel.guild_id == current_user['guild_id'])
    ).all()
    for channel in channels:
        session.delete(channel)

    # Delete all roles (except the ones created by Discord)
    roles = session.exec(
        select(Role).where(Role.guild_id == current_user['guild_id'])
    ).all()
    for role in roles:
        session.delete(role)

    # Reset guild settings
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user['guild_id'])
    ).first()

    if guild:
        guild.settings = {
            'welcome_enabled': True,
            'auto_role': True,
            'set_nickname': True,
            'require_email': False
        }
        from sqlalchemy.orm import attributes
        attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user['guild_id'],
        user_id=current_user['discord_id'],
        discord_username=current_user['username'],
        action="configuration_reset",
        details={"reset_by": current_user['username']}
    )
    session.add(audit_log)
    session.commit()

    logger.warning(f"Configuration reset by {current_user['username']}")

    return {"message": "Configuration reset successfully"}