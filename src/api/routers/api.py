"""REST API router for JSON endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import logging

from src.shared.database import get_session
from src.shared.models import Member, Guild, Config, AuditLog, Role, Channel
from src.api.routers.auth import get_current_user
from src.api.models.schemas import (
    MemberResponse,
    GuildResponse,
    ConfigResponse,
    StatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: Session = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get server statistics"""
    if current_user["is_super_admin"]:
        total_guilds = session.exec(select(Guild)).all()
        total_members = session.exec(select(Member)).all()
    else:
        total_guilds = session.exec(
            select(Guild).where(Guild.guild_id == current_user["guild_id"])
        ).all()
        total_members = session.exec(
            select(Member).where(Member.guild_id == current_user["guild_id"])
        ).all()

    onboarded = [m for m in total_members if m.onboarding_status > 0]

    return StatsResponse(
        total_guilds=len(total_guilds),
        total_members=len(total_members),
        onboarded_members=len(onboarded),
        pending_members=len(total_members) - len(onboarded),
    )


@router.get("/users", response_model=List[MemberResponse])
async def get_users(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    onboarded_only: bool = False,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get list of users"""
    query = select(Member)

    # Filter by guild if not super admin
    if not current_user["is_super_admin"]:
        query = query.where(Member.guild_id == current_user["guild_id"])

    # Search filter
    if search:
        query = query.where(
            (Member.username.contains(search))
            | (Member.nickname.contains(search))
            | (Member.firstname.contains(search))
            | (Member.lastname.contains(search))
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
    current_user=Depends(get_current_user),
):
    """Get single user details"""
    user = session.exec(select(Member).where(Member.id == user_id)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user["is_super_admin"] and user.guild_id != current_user["guild_id"]:
        raise HTTPException(403, "Access denied")

    return MemberResponse.from_orm(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Delete a user from the database and reset their Discord nickname"""
    user = session.exec(select(Member).where(Member.id == user_id)).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check permission
    if not current_user["is_super_admin"] and user.guild_id != current_user["guild_id"]:
        raise HTTPException(403, "Access denied")

    # Reset Discord nickname and remove role (before deleting from DB)
    discord_updated = False
    try:
        # Access bot instance from FastAPI app state
        bot_instance = getattr(request.app.state, "bot", None)
        logger.info(
            f"Attempting to reset Discord state for {user.username} (ID: {user.user_id}, Guild: {user.guild_id})"
        )

        if bot_instance and bot_instance.user:
            logger.info(f"Bot instance found: {bot_instance.user.name}")
            guild = bot_instance.get_guild(user.guild_id)

            if guild:
                logger.info(f"Guild found: {guild.name} (ID: {guild.id})")
                member = guild.get_member(user.user_id)

                if member:
                    logger.info(
                        f"Member found: {member.name} (current nick: {member.nick})"
                    )
                    # Reset nickname
                    try:
                        await member.edit(nick=None)
                        logger.info(f"✓ Reset nickname for {user.username}")
                        discord_updated = True
                    except Exception as e:
                        logger.warning(
                            f"Could not reset nickname for {user.username}: {e}"
                        )

                    # Remove onboarded role
                    try:
                        onboarded_role = session.exec(
                            select(Role).where(
                                Role.guild_id == user.guild_id,
                                Role.role_type == "onboarded",
                            )
                        ).first()
                        if onboarded_role:
                            role = guild.get_role(onboarded_role.role_id)
                            if role and role in member.roles:
                                await member.remove_roles(role)
                                logger.info(
                                    f"✓ Removed onboarded role from {user.username}"
                                )
                        else:
                            logger.info(
                                f"No onboarded role configured for guild {user.guild_id}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Could not remove role from {user.username}: {e}"
                        )
                else:
                    logger.warning(
                        f"✗ Member {user.user_id} not found in guild {user.guild_id}"
                    )
            else:
                logger.warning(
                    f"✗ Guild {user.guild_id} not found. Bot is in guilds: {[g.id for g in bot_instance.guilds]}"
                )
        else:
            logger.warning(
                f"✗ Bot instance not ready (instance: {bot_instance}, has user: {bot_instance.user if bot_instance else 'N/A'})"
            )
    except ImportError:
        logger.warning("✗ Bot instance not available, cannot reset Discord nickname")
    except Exception as e:
        logger.error(f"✗ Error resetting Discord state for {user.username}: {e}")

    # Log the deletion
    audit_log = AuditLog(
        guild_id=user.guild_id,
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="user_deleted",
        details={
            "deleted_user_id": user.user_id,
            "deleted_username": user.username,
            "deleted_by": current_user["username"],
            "discord_updated": discord_updated,
        },
    )
    session.add(audit_log)

    # Delete the user
    session.delete(user)
    session.commit()

    logger.info(
        f"User {user.username} (ID: {user.user_id}) deleted by {current_user['username']}"
    )

    return {
        "message": "User deleted successfully",
        "user_id": user_id,
        "discord_updated": discord_updated,
    }


@router.get("/guilds", response_model=List[GuildResponse])
async def get_guilds(
    session: Session = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get list of guilds (super admin only)"""
    if not current_user["is_super_admin"]:
        # Regular admin only sees their guild
        guilds = session.exec(
            select(Guild).where(Guild.guild_id == current_user["guild_id"])
        ).all()
    else:
        guilds = session.exec(select(Guild)).all()

    return [GuildResponse.from_orm(g) for g in guilds]


@router.get("/config", response_model=List[ConfigResponse])
async def get_configs(
    session: Session = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get all configuration values"""
    configs = session.exec(
        select(Config).where(Config.guild_id == current_user["guild_id"])
    ).all()

    return [ConfigResponse.from_orm(c) for c in configs]


@router.get("/users/export")
async def export_users(
    format: str = Query("csv", regex="^(csv|json)$"),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Export users data"""
    query = select(Member)

    if not current_user["is_super_admin"]:
        query = query.where(Member.guild_id == current_user["guild_id"])

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
                "join_date": m.join_datetime.isoformat() if m.join_datetime else None,
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
        writer.writerow(
            [
                "User ID",
                "Username",
                "Nickname",
                "First Name",
                "Last Name",
                "Email",
                "Onboarding Status",
                "Join Date",
            ]
        )

        # Data
        for m in members:
            writer.writerow(
                [
                    m.user_id,
                    m.username,
                    m.nickname,
                    m.firstname,
                    m.lastname,
                    m.email,
                    m.onboarding_status,
                    m.join_datetime.isoformat() if m.join_datetime else "",
                ]
            )

        from fastapi.responses import Response

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            },
        )


@router.post("/config/channel")
async def configure_channel(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Configure a channel for the guild"""
    data = await request.json()
    channel_id_raw = data.get("channel_id")
    channel_type = data.get("channel_type")
    name = data.get("name")

    if not channel_id_raw or not channel_type:
        raise HTTPException(400, "channel_id and channel_type are required")

    # Convert channel_id to int, handling both string and int input
    try:
        channel_id = int(channel_id_raw)
    except (ValueError, TypeError):
        raise HTTPException(400, "channel_id must be a valid integer")

    # Check if channel already exists
    existing_channel = session.exec(
        select(Channel).where(
            Channel.guild_id == current_user["guild_id"],
            Channel.channel_type == channel_type,
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
            guild_id=current_user["guild_id"],
            name=name,
            enabled=True,
        )
        session.add(channel)

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="channel_configured",
        details={"channel_id": channel_id, "channel_type": channel_type, "name": name},
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Channel {channel_type} configured by {current_user['username']}")

    return {"message": "Channel configured successfully"}


@router.post("/config/role")
async def configure_role(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Configure a role for the guild"""
    data = await request.json()
    role_id_raw = data.get("role_id")
    role_type = data.get("role_type")
    role_name = data.get("role_name")

    if not role_id_raw or not role_type or not role_name:
        raise HTTPException(400, "role_id, role_type, and role_name are required")

    # Convert role_id to int
    try:
        role_id = int(role_id_raw)
    except (ValueError, TypeError):
        raise HTTPException(400, f"Invalid role_id: {role_id_raw}")

    logger.info(
        f"Configuring role: role_id={role_id} (type={type(role_id)}), role_type={role_type}, role_name={role_name}, guild_id={current_user['guild_id']}"
    )

    # For approver roles, we allow multiple roles of the same type
    if role_type == "onboarding_approver":
        # Check if this specific role_id already exists for this type
        existing_role = session.exec(
            select(Role).where(
                Role.guild_id == current_user["guild_id"],
                Role.role_type == role_type,
                Role.role_id == role_id,
            )
        ).first()

        if existing_role:
            # Update existing role
            existing_role.role_name = role_name
        else:
            # Create new role
            role = Role(
                role_id=role_id,
                role_name=role_name,
                role_type=role_type,
                guild_id=current_user["guild_id"],
            )
            session.add(role)
    else:
        # For other role types, only one role per type
        existing_role = session.exec(
            select(Role).where(
                Role.guild_id == current_user["guild_id"], Role.role_type == role_type
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
                guild_id=current_user["guild_id"],
            )
            session.add(role)

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="role_configured",
        details={"role_id": role_id, "role_type": role_type, "role_name": role_name},
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Role {role_type} configured by {current_user['username']}")

    return {"message": "Role configured successfully"}


@router.post("/config/role/delete")
async def delete_role(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Delete a role configuration"""
    data = await request.json()
    role_id = data.get("role_id")
    role_type = data.get("role_type")

    if not role_id or not role_type:
        raise HTTPException(400, "role_id and role_type are required")

    # Find the role
    role = session.exec(
        select(Role).where(
            Role.guild_id == current_user["guild_id"],
            Role.role_id == role_id,
            Role.role_type == role_type,
        )
    ).first()

    if not role:
        raise HTTPException(404, "Role not found")

    # Delete the role
    session.delete(role)

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="role_deleted",
        details={"role_id": role_id, "role_type": role_type},
    )
    session.add(audit_log)
    session.commit()

    logger.info(
        f"Role {role_type} (ID: {role_id}) deleted by {current_user['username']}"
    )

    return {"message": "Role deleted successfully"}


@router.post("/config/setting")
async def update_setting(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update a guild setting"""
    data = await request.json()
    key = data.get("key")
    value = data.get("value")

    if not key:
        raise HTTPException(400, "key is required")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
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
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="setting_updated",
        details={"key": key, "value": value},
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Setting {key} updated to {value} by {current_user['username']}")

    return {"message": "Setting updated successfully"}


@router.post("/config/welcome-message")
async def update_welcome_message(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update welcome message configuration"""
    data = await request.json()
    message_type = data.get("type", "embed")

    if message_type not in ["embed", "plain"]:
        raise HTTPException(400, "type must be 'embed' or 'plain'")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    if not guild:
        raise HTTPException(404, "Guild not found")

    # Update settings
    if guild.settings is None:
        guild.settings = {}

    # Build welcome message configuration
    welcome_config = {"type": message_type}

    if message_type == "plain":
        welcome_config["content"] = data.get("content", "")
    else:
        # Embed configuration
        embed_config = {
            "title": data.get("title", "Welcome to the Server!"),
            "description": data.get("description", ""),
            "color": data.get("color", "green"),
            "footer": data.get("footer", ""),
        }

        # Add fields if provided
        fields = data.get("fields", [])
        if fields:
            embed_config["fields"] = fields

        welcome_config["embed"] = embed_config

    guild.settings["welcome_message_config"] = welcome_config

    # Force SQLAlchemy to detect the change
    from sqlalchemy.orm import attributes

    attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="welcome_message_updated",
        details={"type": message_type},
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Welcome message configuration updated by {current_user['username']}")

    return {"message": "Welcome message configuration updated successfully"}


@router.get("/discord/channels")
async def get_discord_channels(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get all text channels from Discord for the guild"""
    try:
        # Get bot instance from app state
        bot = getattr(request.app.state, "bot", None)

        if not bot or not bot.is_ready():
            return {"channels": [], "error": "Bot is not connected to Discord"}

        # Get the Discord guild
        discord_guild = bot.get_guild(current_user["guild_id"])

        if not discord_guild:
            return {"channels": [], "error": "Guild not found in Discord"}

        # Get all text channels
        channels = []
        for channel in discord_guild.text_channels:
            channels.append(
                {
                    "id": str(channel.id),
                    "name": channel.name,
                    "category": channel.category.name if channel.category else None,
                }
            )

        # Sort by category and name
        channels.sort(key=lambda x: (x["category"] or "", x["name"]))

        return {"channels": channels, "error": None}

    except Exception as e:
        logger.error(f"Error fetching Discord channels: {e}")
        return {"channels": [], "error": str(e)}


@router.get("/discord/roles")
async def get_discord_roles(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get all roles from Discord for the guild"""
    try:
        # Get bot instance from app state
        bot = getattr(request.app.state, "bot", None)

        if not bot or not bot.is_ready():
            return {"roles": [], "error": "Bot is not connected to Discord"}

        # Get the Discord guild
        discord_guild = bot.get_guild(current_user["guild_id"])

        if not discord_guild:
            return {"roles": [], "error": "Guild not found in Discord"}

        # Get all roles (excluding @everyone)
        roles = []
        for role in discord_guild.roles:
            if role.name != "@everyone":
                roles.append(
                    {
                        "id": str(role.id),
                        "name": role.name,
                        "color": str(role.color),
                        "position": role.position,
                    }
                )

        # Sort by position (highest first)
        roles.sort(key=lambda x: x["position"], reverse=True)

        return {"roles": roles, "error": None}

    except Exception as e:
        logger.error(f"Error fetching Discord roles: {e}")
        return {"roles": [], "error": str(e)}


@router.post("/welcome/update-message")
async def update_welcome_message_endpoint(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update the existing welcome message with new content"""
    try:
        # Get bot instance
        bot = getattr(request.app.state, "bot", None)
        if not bot or not bot.is_ready():
            raise HTTPException(503, "Bot is not connected to Discord")

        # Get welcome channel
        welcome_channel = session.exec(
            select(Channel).where(
                Channel.guild_id == current_user["guild_id"],
                Channel.channel_type == "welcome",
            )
        ).first()

        if not welcome_channel:
            raise HTTPException(404, "Welcome channel not configured")

        if not welcome_channel.message_id:
            raise HTTPException(
                404,
                "No welcome message exists yet. Use 'Send/Replace Message' instead.",
            )

        # Update the message
        success, message = await bot.update_welcome_message(
            current_user["guild_id"],
            welcome_channel.channel_id,
            welcome_channel.message_id,
        )

        if not success:
            raise HTTPException(500, f"Failed to update message: {message}")

        # Log the action
        audit_log = AuditLog(
            guild_id=current_user["guild_id"],
            user_id=current_user["discord_id"],
            discord_username=current_user["username"],
            action="welcome_message_updated",
            details={"message_id": welcome_channel.message_id},
        )
        session.add(audit_log)
        session.commit()

        logger.info(f"Welcome message updated by {current_user['username']}")
        return {"message": "Welcome message updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating welcome message: {e}")
        raise HTTPException(500, f"Error updating welcome message: {str(e)}")


@router.post("/welcome/replace-message")
async def replace_welcome_message_endpoint(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Delete the old welcome message and create a new one (or create if none exists)"""
    try:
        # Get bot instance
        bot = getattr(request.app.state, "bot", None)
        if not bot or not bot.is_ready():
            raise HTTPException(503, "Bot is not connected to Discord")

        # Get welcome channel
        welcome_channel = session.exec(
            select(Channel).where(
                Channel.guild_id == current_user["guild_id"],
                Channel.channel_type == "welcome",
            )
        ).first()

        if not welcome_channel:
            raise HTTPException(404, "Welcome channel not configured")

        logger.info(
            f"Replacing welcome message for guild {current_user['guild_id']}, "
            f"channel {welcome_channel.channel_id}, message {welcome_channel.message_id}"
        )

        # Replace/create the message
        success, message, new_message_id = await bot.replace_welcome_message(
            current_user["guild_id"],
            welcome_channel.channel_id,
            welcome_channel.message_id,
        )

        logger.info(
            f"Replace result: success={success}, message={message}, new_id={new_message_id}"
        )

        if not success:
            raise HTTPException(500, f"Failed to replace message: {message}")

        # Update the message ID in database
        welcome_channel.message_id = new_message_id
        session.add(welcome_channel)

        # Log the action
        audit_log = AuditLog(
            guild_id=current_user["guild_id"],
            user_id=current_user["discord_id"],
            discord_username=current_user["username"],
            action="welcome_message_replaced",
            details={"new_message_id": new_message_id},
        )
        session.add(audit_log)
        session.commit()

        logger.info(f"Welcome message replaced by {current_user['username']}")
        return {
            "message": "Welcome message created/replaced successfully",
            "message_id": new_message_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing welcome message: {e}")
        raise HTTPException(500, f"Error replacing welcome message: {str(e)}")


@router.post("/config/reset")
async def reset_configuration(
    session: Session = Depends(get_session), current_user=Depends(get_current_user)
):
    """Reset all configuration for the guild"""
    # Delete all channels
    channels = session.exec(
        select(Channel).where(Channel.guild_id == current_user["guild_id"])
    ).all()
    for channel in channels:
        session.delete(channel)

    # Delete all roles (except the ones created by Discord)
    roles = session.exec(
        select(Role).where(Role.guild_id == current_user["guild_id"])
    ).all()
    for role in roles:
        session.delete(role)

    # Reset guild settings
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    if guild:
        guild.settings = {
            "welcome_enabled": True,
            "auto_role": True,
            "set_nickname": True,
            "require_email": False,
        }
        from sqlalchemy.orm import attributes

        attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="configuration_reset",
        details={"reset_by": current_user["username"]},
    )
    session.add(audit_log)
    session.commit()

    logger.warning(f"Configuration reset by {current_user['username']}")

    return {"message": "Configuration reset successfully"}


@router.post("/apps/toggle")
async def toggle_app(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Toggle an app on or off"""
    data = await request.json()
    app_name = data.get("app_name")
    enabled = data.get("enabled")

    if not app_name:
        raise HTTPException(400, "app_name is required")

    # Map app names to setting keys
    app_settings_map = {
        "welcome_system": "welcome_enabled",
        "onboarding": "onboarding_enabled",
        "member_management": "member_management_enabled",
        "member_support": "member_support_enabled",
        "slash_commands": "slash_commands_enabled",
    }

    setting_key = app_settings_map.get(app_name)
    if not setting_key:
        raise HTTPException(400, f"Unknown app: {app_name}")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    if not guild:
        raise HTTPException(404, "Guild not found")

    # Update settings
    if guild.settings is None:
        guild.settings = {}

    # Handle app dependencies
    dependencies = {
        "onboarding": ["welcome_system"],  # Onboarding requires Welcome System
        "member_support": ["welcome_system"],  # Member Support requires Welcome System
    }

    # If enabling an app with dependencies, auto-enable dependencies
    if enabled and app_name in dependencies:
        for dependency in dependencies[app_name]:
            dependency_key = app_settings_map.get(dependency)
            if dependency_key:
                guild.settings[dependency_key] = True
                logger.info(f"Auto-enabled {dependency} as dependency of {app_name}")

    guild.settings[setting_key] = enabled

    # Force SQLAlchemy to detect the change
    from sqlalchemy.orm import attributes

    attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="app_toggled",
        details={"app_name": app_name, "enabled": enabled},
    )
    session.add(audit_log)
    session.commit()

    logger.info(
        f"App {app_name} {'enabled' if enabled else 'disabled'} by {current_user['username']}"
    )

    return {
        "message": f"App {app_name} {'enabled' if enabled else 'disabled'} successfully"
    }


@router.post("/commands/permissions")
async def save_command_permissions(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Save slash command permissions"""
    data = await request.json()
    allowed_roles = data.get("allowed_roles", [])

    # Validate that all role IDs are integers
    try:
        allowed_roles = [int(role_id) for role_id in allowed_roles]
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid role IDs provided")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    if not guild:
        raise HTTPException(404, "Guild not found")

    # Update settings
    if guild.settings is None:
        guild.settings = {}

    guild.settings["commands_allowed_roles"] = allowed_roles

    # Force SQLAlchemy to detect the change
    from sqlalchemy.orm import attributes

    attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="command_permissions_updated",
        details={"allowed_roles": allowed_roles},
    )
    session.add(audit_log)
    session.commit()

    logger.info(
        f"Command permissions updated by {current_user['username']}: {len(allowed_roles)} roles"
    )

    return {"message": "Command permissions saved successfully"}


@router.post("/config/onboarding/fields")
async def save_onboarding_fields(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Save onboarding form fields configuration"""
    data = await request.json()
    fields = data.get("fields", [])

    # Validate fields
    if len(fields) > 5:
        raise HTTPException(400, "Maximum 5 fields allowed")

    for field in fields:
        if not field.get("name") or not field.get("label"):
            raise HTTPException(400, "Each field must have a name and label")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    if not guild:
        raise HTTPException(404, "Guild not found")

    # Update settings
    if guild.settings is None:
        guild.settings = {}

    guild.settings["onboarding_fields"] = fields

    # Force SQLAlchemy to detect the change
    from sqlalchemy.orm import attributes

    attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="onboarding_fields_updated",
        details={"field_count": len(fields)},
    )
    session.add(audit_log)
    session.commit()

    logger.info(
        f"Onboarding fields updated by {current_user['username']}: {len(fields)} fields"
    )

    return {"message": "Fields saved successfully"}


@router.post("/config/onboarding/nickname-template")
async def save_nickname_template(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Save nickname template configuration"""
    data = await request.json()
    template = data.get("template", "")

    if not template:
        raise HTTPException(400, "Template is required")

    # Get guild
    guild = session.exec(
        select(Guild).where(Guild.guild_id == current_user["guild_id"])
    ).first()

    if not guild:
        raise HTTPException(404, "Guild not found")

    # Update settings
    if guild.settings is None:
        guild.settings = {}

    guild.settings["nickname_template"] = template

    # Force SQLAlchemy to detect the change
    from sqlalchemy.orm import attributes

    attributes.flag_modified(guild, "settings")

    # Log the action
    audit_log = AuditLog(
        guild_id=current_user["guild_id"],
        user_id=current_user["discord_id"],
        discord_username=current_user["username"],
        action="nickname_template_updated",
        details={"template": template},
    )
    session.add(audit_log)
    session.commit()

    logger.info(f"Nickname template updated by {current_user['username']}: {template}")

    return {"message": "Template saved successfully"}
