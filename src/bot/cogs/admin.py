"""Admin commands cog"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import sys
from src.shared.database import get_session
from src.shared.models import Member, AdminUser, AuditLog
from src.bot.permissions import require_command_permission, command_permission_check
from sqlmodel import select

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog):
    """Admin commands for bot management"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_admin(self, user_id: int, guild_id: int) -> bool:
        """Check if user is an admin"""
        with next(get_session()) as session:
            admin = session.exec(
                select(AdminUser).where(
                    AdminUser.discord_id == user_id, AdminUser.guild_id == guild_id
                )
            ).first()
            return admin is not None

    async def remove_member(self, member: discord.Member):
        """Remove member from database and reset nickname"""
        try:
            with next(get_session()) as session:
                # Remove from database
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == member.id, Member.guild_id == member.guild.id
                    )
                ).first()

                if db_member:
                    session.delete(db_member)

                    # Log the action
                    audit_log = AuditLog(
                        guild_id=member.guild.id,
                        user_id=member.id,
                        discord_username=member.name,
                        action="member_removed",
                        details={"removed_by": "admin_command"},
                    )
                    session.add(audit_log)
                    session.commit()

            # Reset Discord nickname
            await member.edit(nick=None)

            # Remove onboarded role if exists
            for role in member.roles:
                if role.name == "Maker" or role.name == "Onboarded":
                    await member.remove_roles(role)

            return True

        except Exception as e:
            logger.error(f"Error removing member: {e}")
            return False

    @app_commands.command(
        name="remove", description="Remove user from database and reset nickname"
    )
    @app_commands.describe(member="The member you want to remove")
    @require_command_permission()
    async def slash_remove(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        """Remove a member's data (admin only)"""
        # Check admin permission
        if not self.is_admin(interaction.user.id, interaction.guild.id):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command", ephemeral=True
            )
            return

        success = await self.remove_member(member)
        if success:
            await interaction.response.send_message(
                f"✅ User {member.display_name} removed", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to remove user {member.display_name}", ephemeral=True
            )

    @app_commands.command(name="stats", description="View server statistics")
    @require_command_permission()
    async def slash_stats(self, interaction: discord.Interaction):
        """View server statistics (admin only)"""
        # Check admin permission
        if not self.is_admin(interaction.user.id, interaction.guild.id):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command", ephemeral=True
            )
            return

        with next(get_session()) as session:
            # Get member statistics
            total_members = session.exec(
                select(Member).where(Member.guild_id == interaction.guild.id)
            ).all()

            onboarded = [m for m in total_members if m.onboarding_status > 0]

        embed = discord.Embed(title="📊 Server Statistics", color=discord.Color.blue())
        embed.add_field(name="Total Members in DB", value=str(len(total_members)))
        embed.add_field(name="Onboarded", value=str(len(onboarded)))
        embed.add_field(
            name="Not Onboarded", value=str(len(total_members) - len(onboarded))
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="list_members", description="List all members in database"
    )
    @require_command_permission()
    async def slash_list_members(self, interaction: discord.Interaction):
        """List all members (admin only)"""
        # Check admin permission
        if not self.is_admin(interaction.user.id, interaction.guild.id):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command", ephemeral=True
            )
            return

        with next(get_session()) as session:
            members = session.exec(
                select(Member).where(Member.guild_id == interaction.guild.id)
            ).all()

        if not members:
            await interaction.response.send_message(
                "No members found in database", ephemeral=True
            )
            return

        # Create pages if too many members
        member_list = []
        for member in members[:20]:  # Limit to first 20
            status = "✅" if member.onboarding_status > 0 else "❌"
            member_list.append(
                f"{status} {member.username} ({member.nickname or 'No nickname'})"
            )

        embed = discord.Embed(
            title="Members in Database",
            description="\n".join(member_list),
            color=discord.Color.green(),
        )

        if len(members) > 20:
            embed.set_footer(text=f"Showing 20 of {len(members)} members")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="shutdown")
    @commands.is_owner()  # Only bot owner can shutdown
    @command_permission_check()
    async def cmd_shutdown(self, ctx: commands.Context):
        """Shutdown the bot (owner only)"""
        await ctx.send("Shutting down! 👋")
        await self.bot.close()
        sys.exit(0)

    @app_commands.command(name="sync", description="Sync slash commands")
    @require_command_permission()
    async def slash_sync(self, interaction: discord.Interaction):
        """Sync slash commands (admin only)"""
        # Check admin permission
        if not self.is_admin(interaction.user.id, interaction.guild.id):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(
                f"✅ Synced {len(synced)} commands", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to sync commands: {e}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function to add cog to bot"""
    await bot.add_cog(AdminCog(bot))
