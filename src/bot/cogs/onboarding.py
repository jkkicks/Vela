"""Onboarding cog for member management"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from src.shared.database import get_session
from src.shared.models import Member, Role, AuditLog
from sqlmodel import select

logger = logging.getLogger(__name__)


class OnboardingCog(commands.Cog):
    """Handles member onboarding functionality"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def update_member_nickname(
        self,
        member: discord.Member,
        firstname: str,
        lastname: str
    ):
        """Update member's server nickname"""
        nickname = f"{firstname} {lastname}"

        try:
            with next(get_session()) as session:
                # Update database
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == member.id,
                        Member.guild_id == member.guild.id
                    )
                ).first()

                if db_member:
                    db_member.nickname = nickname
                    db_member.firstname = firstname
                    db_member.lastname = lastname
                    db_member.last_change_datetime = datetime.utcnow()
                    session.commit()

                    # Log the action
                    audit_log = AuditLog(
                        guild_id=member.guild.id,
                        user_id=member.id,
                        discord_username=member.name,
                        action="nickname_update",
                        details={
                            "firstname": firstname,
                            "lastname": lastname,
                            "nickname": nickname
                        }
                    )
                    session.add(audit_log)
                    session.commit()

            # Update Discord nickname
            await member.edit(nick=nickname)
            logger.info(f'Updated nickname for {member.name} to {nickname}')
            return True

        except Exception as e:
            logger.error(f"Error updating nickname: {e}")
            return False

    async def complete_onboarding(self, member: discord.Member):
        """Mark member as onboarded and assign role"""
        try:
            with next(get_session()) as session:
                # Update member status
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == member.id,
                        Member.guild_id == member.guild.id
                    )
                ).first()

                if db_member:
                    db_member.onboarding_status = 1
                    db_member.onboarding_completed_at = datetime.utcnow()
                    session.commit()

                # Get onboarded role from database
                onboarded_role = session.exec(
                    select(Role).where(
                        Role.guild_id == member.guild.id,
                        Role.role_type == "onboarded"
                    )
                ).first()

                # Log the action
                audit_log = AuditLog(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    discord_username=member.name,
                    action="onboarding_completed",
                    details={"status": "completed"}
                )
                session.add(audit_log)
                session.commit()

            # Assign role if configured
            if onboarded_role:
                role = member.guild.get_role(onboarded_role.role_id)
                if role:
                    await member.add_roles(role)
                    logger.info(f"Assigned role {role.name} to {member.name}")

            return True

        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            return False

    @commands.command(name='reinit')
    async def cmd_reinit(self, ctx: commands.Context):
        """Re-initialize a user in the database"""
        try:
            with next(get_session()) as session:
                # Check if member exists
                db_member = session.exec(
                    select(Member).where(
                        Member.user_id == ctx.author.id,
                        Member.guild_id == ctx.guild.id
                    )
                ).first()

                if not db_member:
                    # Add member
                    new_member = Member(
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id,
                        username=ctx.author.name,
                        join_datetime=ctx.author.joined_at,
                        onboarding_status=0
                    )
                    session.add(new_member)
                    session.commit()

            await ctx.send("✅ Reinitialized!")
        except Exception as e:
            logger.error(f"Error in reinit command: {e}")
            await ctx.send("❌ Error reinitializing user")

    @commands.command(name='nick')
    async def cmd_nick(self, ctx: commands.Context):
        """View current nickname"""
        await ctx.send(f'You are {ctx.author.nick or ctx.author.name}')

    @commands.command(name='setnick')
    async def cmd_setnick(self, ctx: commands.Context, firstname: str, lastname: str):
        """Change nickname (use two words separated by a space)"""
        success = await self.update_member_nickname(ctx.author, firstname, lastname)
        if success:
            await ctx.send(f'✅ You are now {ctx.author.nick}')
        else:
            await ctx.send('❌ Failed to update nickname')

    @app_commands.command(name="onboard", description="Complete your onboarding")
    @app_commands.describe(
        firstname="Your first name",
        lastname="Your last name"
    )
    async def slash_onboard(
        self,
        interaction: discord.Interaction,
        firstname: str,
        lastname: str
    ):
        """Slash command for onboarding"""
        # Check if already onboarded
        with next(get_session()) as session:
            db_member = session.exec(
                select(Member).where(
                    Member.user_id == interaction.user.id,
                    Member.guild_id == interaction.guild.id
                )
            ).first()

            if db_member and db_member.onboarding_status > 0:
                await interaction.response.send_message(
                    "You have already completed onboarding! To change your name, use /setnick",
                    ephemeral=True
                )
                return

        # Update nickname
        success = await self.update_member_nickname(
            interaction.user,
            firstname,
            lastname
        )

        if success:
            # Complete onboarding
            await self.complete_onboarding(interaction.user)
            await interaction.response.send_message(
                f"✅ Welcome {firstname} {lastname}! Your onboarding is complete.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ There was an error completing your onboarding. Please try again or contact an admin.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function to add cog to bot"""
    await bot.add_cog(OnboardingCog(bot))