"""Command permission checking utilities"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Union, Optional
from src.shared.database import get_session
from src.shared.models import Guild
from sqlmodel import select

logger = logging.getLogger(__name__)


def check_command_permissions(
    guild_id: int, user: Union[discord.Member, discord.User]
) -> tuple[bool, Optional[str]]:
    """
    Check if a user has permission to use commands.

    Returns:
        tuple[bool, Optional[str]]: (has_permission, error_message)
    """
    # If user is not a Member (in DMs), deny
    if not isinstance(user, discord.Member):
        return False, "Commands can only be used in servers."

    # Server administrators always have permission
    if user.guild_permissions.administrator:
        return True, None

    try:
        with next(get_session()) as session:
            # Get guild settings
            guild = session.exec(
                select(Guild).where(Guild.guild_id == guild_id)
            ).first()

            if not guild:
                # Guild not in database, allow by default
                return True, None

            # Check if commands are globally enabled
            commands_enabled = guild.settings.get("slash_commands_enabled", True)
            if not commands_enabled:
                return False, "❌ Bot commands are currently disabled."

            # Get allowed roles
            allowed_roles = guild.settings.get("commands_allowed_roles", [])

            # If no roles configured, allow all users
            if not allowed_roles or len(allowed_roles) == 0:
                return True, None

            # Check if user has any of the allowed roles
            user_role_ids = [role.id for role in user.roles]
            has_required_role = any(
                role_id in user_role_ids for role_id in allowed_roles
            )

            if not has_required_role:
                return (
                    False,
                    "❌ You don't have permission to use bot commands. Contact a server administrator if you believe this is an error.",
                )

            return True, None

    except Exception as e:
        logger.error(f"Error checking command permissions: {e}")
        # On error, allow command (fail open to avoid blocking all commands)
        return True, None


# Decorator for app commands (slash commands)
def require_command_permission():
    """Decorator to check permissions for app commands (slash commands)"""

    async def predicate(interaction: discord.Interaction) -> bool:
        has_permission, error_message = check_command_permissions(
            interaction.guild_id, interaction.user
        )

        if not has_permission:
            await interaction.response.send_message(error_message, ephemeral=True)
            return False

        return True

    return app_commands.check(predicate)


# Check for regular commands (prefix commands)
def command_permission_check():
    """Check function for regular prefix commands"""

    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            await ctx.send("❌ Commands can only be used in servers.")
            return False

        has_permission, error_message = check_command_permissions(
            ctx.guild.id, ctx.author
        )

        if not has_permission:
            await ctx.send(error_message)
            return False

        return True

    return commands.check(predicate)
