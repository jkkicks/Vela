"""Background task for syncing Discord messages with database state"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import discord
from sqlmodel import Session, select
from src.shared.database import get_session
from src.shared.models import Guild, Member, Channel, AuditLog

logger = logging.getLogger(__name__)


class SyncTask:
    """
    Periodically checks for Discord messages that may be out of sync
    and syncs them with the actual database state.
    """

    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.stats = {
            "total_runs": 0,
            "messages_checked": 0,
            "messages_updated": 0,
            "errors": 0,
        }

    async def start(self):
        """Start the sync background task"""
        if self.running:
            logger.warning("Sync task already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("Sync task started")

    async def stop(self):
        """Stop the sync background task gracefully"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Onboarding sync task stopped")

    async def _run_loop(self):
        """Main loop for the sync task"""
        while self.running:
            try:
                # Check if sync is enabled
                if await self._is_enabled():
                    interval_minutes = await self._get_interval()
                    await self.sync_all_guilds()
                    # Wait for the configured interval
                    await asyncio.sleep(interval_minutes * 60)
                else:
                    # If disabled, check less frequently
                    await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}", exc_info=True)
                self.stats["errors"] += 1
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def _is_enabled(self) -> bool:
        """Check if sync is enabled globally"""
        with next(get_session()) as session:
            # Check any guild has sync enabled
            guilds = session.exec(select(Guild).where(Guild.is_active)).all()
            for guild in guilds:
                if guild.settings and guild.settings.get("sync_enabled", False):
                    return True
        return False

    async def _get_interval(self) -> int:
        """Get the sync interval in minutes"""
        with next(get_session()) as session:
            # Get the first active guild's interval setting
            guilds = session.exec(select(Guild).where(Guild.is_active)).all()
            for guild in guilds:
                if guild.settings and guild.settings.get("sync_enabled", False):
                    return guild.settings.get("sync_interval_minutes", 15)
        return 15  # Default to 15 minutes

    async def sync_all_guilds(self):
        """Run sync for all guilds with the feature enabled"""
        self.last_run = datetime.utcnow()
        self.stats["total_runs"] += 1

        with next(get_session()) as session:
            guilds = session.exec(select(Guild).where(Guild.is_active)).all()

            for guild in guilds:
                if not guild.settings or not guild.settings.get("sync_enabled", False):
                    continue

                try:
                    await self.sync_guild(guild.guild_id)
                except Exception as e:
                    logger.error(
                        f"Error reconciling guild {guild.guild_id}: {e}", exc_info=True
                    )
                    self.stats["errors"] += 1

    async def sync_guild(self, guild_id: int):
        """sync approval messages for a specific guild"""
        logger.info(f"Starting sync for guild {guild_id}")

        # Get the Discord guild
        guild = self.bot.get_guild(guild_id)
        if not guild:
            logger.warning(f"Guild {guild_id} not found in bot cache")
            return

        with next(get_session()) as session:
            # Get the approval channel
            approval_channel = session.exec(
                select(Channel).where(
                    Channel.guild_id == guild_id,
                    Channel.channel_type == "onboarding_approval",
                )
            ).first()

            if not approval_channel:
                logger.debug(f"No approval channel configured for guild {guild_id}")
                return

            # Get guild settings
            db_guild = session.exec(
                select(Guild).where(Guild.guild_id == guild_id)
            ).first()

            if not db_guild or not db_guild.settings:
                return

            lookback_hours = db_guild.settings.get("sync_lookback_hours", 24)

        # Get the Discord channel
        channel = guild.get_channel(approval_channel.channel_id)
        if not channel:
            logger.warning(f"Approval channel {approval_channel.channel_id} not found")
            return

        # Fetch recent messages
        messages_to_check = []
        after_time = datetime.utcnow() - timedelta(hours=lookback_hours)

        try:
            async for message in channel.history(limit=100, after=after_time):
                # Check if this is an approval request message
                if (
                    message.author.id == self.bot.user.id
                    and message.embeds
                    and len(message.embeds) > 0
                ):
                    embed = message.embeds[0]
                    # Look for approval request embeds
                    if "Onboarding Approval Request" in (embed.title or ""):
                        messages_to_check.append(message)
                        self.stats["messages_checked"] += 1

        except discord.Forbidden:
            logger.error(f"No permission to read messages in channel {channel.id}")
            return
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return

        logger.info(f"Found {len(messages_to_check)} approval messages to check")

        # Check each message
        for message in messages_to_check:
            await self._sync_message(message, guild_id)

    async def _sync_message(self, message: discord.Message, guild_id: int):
        """sync a single approval message with database state"""
        try:
            # Extract user ID from the embed
            user_id = self._extract_user_id_from_embed(message.embeds[0])
            if not user_id:
                logger.warning(f"Could not extract user ID from message {message.id}")
                return

            # Check database state
            with next(get_session()) as session:
                member = session.exec(
                    select(Member).where(
                        Member.guild_id == guild_id,
                        Member.user_id == user_id,
                    )
                ).first()

                if not member:
                    logger.debug(f"No member record found for user {user_id}")
                    return

                # Check if already processed but message not updated
                if member.onboarding_status == 1:  # Approved
                    await self._update_approved_message(message, member, session)
                elif member.onboarding_status == -1:  # Denied
                    await self._update_denied_message(message, member, session)
                # If status is 0 (pending), leave the message as is

        except Exception as e:
            logger.error(f"Error reconciling message {message.id}: {e}", exc_info=True)
            self.stats["errors"] += 1

    def _extract_user_id_from_embed(self, embed: discord.Embed) -> Optional[int]:
        """Extract user ID from approval request embed"""
        # Look for User ID in fields
        for field in embed.fields:
            if field.name == "User ID":
                try:
                    return int(field.value)
                except (ValueError, TypeError):
                    pass

        # Try to extract from description (fallback)
        if embed.description:
            # Look for mentions in format <@USER_ID>
            import re

            match = re.search(r"<@(\d+)>", embed.description)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        return None

    async def _update_approved_message(
        self, message: discord.Message, member: Member, session: Session
    ):
        """Update a message to show approved status"""
        try:
            # Check if message already shows approved status
            embed = message.embeds[0]
            if "✅" in (embed.title or "") or "Approved" in (embed.title or ""):
                logger.debug(f"Message {message.id} already shows approved status")
                return

            # Find who approved from audit log
            approver_info = "System (sync)"
            audit_log = session.exec(
                select(AuditLog).where(
                    AuditLog.guild_id == member.guild_id,
                    AuditLog.action
                    == "onboarding_approved",  # Changed from action_type to action
                )
            ).all()

            for log in audit_log:
                if log.details and log.details.get("approved_user_id") == str(
                    member.user_id
                ):
                    approver_info = log.discord_username or "Unknown"
                    break

            # Create updated embed
            new_embed = discord.Embed(
                title="✅ Onboarding Request Approved",
                description=embed.description,
                color=discord.Color.green(),
                timestamp=member.onboarding_completed_at or datetime.utcnow(),
            )

            # Copy existing fields
            for field in embed.fields:
                if field.name != "Approved By":
                    new_embed.add_field(
                        name=field.name, value=field.value, inline=field.inline
                    )

            # Add approved by field
            new_embed.add_field(name="Approved By", value=approver_info, inline=False)

            # Set footer and thumbnail if present
            if embed.footer:
                new_embed.set_footer(text=embed.footer.text)
            if embed.thumbnail:
                new_embed.set_thumbnail(url=embed.thumbnail.url)

            # Update the message with disabled buttons
            await message.edit(embed=new_embed, view=None)
            logger.info(f"Updated message {message.id} to show approved status")
            self.stats["messages_updated"] += 1

            # Log the sync
            sync_log = AuditLog(
                guild_id=member.guild_id,
                user_id=member.user_id,
                discord_username=member.nickname or "Unknown",
                action="sync_approved",  # Changed from action_type to action
                details={
                    "message_id": str(message.id),
                    "original_approver": approver_info,
                    "sync_time": datetime.utcnow().isoformat(),
                },
            )
            session.add(sync_log)
            session.commit()

        except Exception as e:
            logger.error(f"Error updating approved message {message.id}: {e}")
            self.stats["errors"] += 1

    async def _update_denied_message(
        self, message: discord.Message, member: Member, session: Session
    ):
        """Update a message to show denied status"""
        try:
            # Check if message already shows denied status
            embed = message.embeds[0]
            if "❌" in (embed.title or "") or "Denied" in (embed.title or ""):
                logger.debug(f"Message {message.id} already shows denied status")
                return

            # Find who denied from audit log
            denier_info = "System (sync)"
            audit_log = session.exec(
                select(AuditLog).where(
                    AuditLog.guild_id == member.guild_id,
                    AuditLog.action
                    == "onboarding_denied",  # Changed from action_type to action
                )
            ).all()

            for log in audit_log:
                if log.details and log.details.get("denied_user_id") == str(
                    member.user_id
                ):
                    denier_info = log.discord_username or "Unknown"
                    break

            # Create updated embed
            new_embed = discord.Embed(
                title="❌ Onboarding Request Denied",
                description=embed.description,
                color=discord.Color.red(),
                timestamp=datetime.utcnow(),
            )

            # Copy existing fields
            for field in embed.fields:
                if field.name != "Denied By":
                    new_embed.add_field(
                        name=field.name, value=field.value, inline=field.inline
                    )

            # Add denied by field
            new_embed.add_field(name="Denied By", value=denier_info, inline=False)

            # Set footer and thumbnail if present
            if embed.footer:
                new_embed.set_footer(text=embed.footer.text)
            if embed.thumbnail:
                new_embed.set_thumbnail(url=embed.thumbnail.url)

            # Update the message with disabled buttons
            await message.edit(embed=new_embed, view=None)
            logger.info(f"Updated message {message.id} to show denied status")
            self.stats["messages_updated"] += 1

            # Log the sync
            sync_log = AuditLog(
                guild_id=member.guild_id,
                user_id=member.user_id,
                discord_username=member.nickname or "Unknown",
                action="sync_denied",  # Changed from action_type to action
                details={
                    "message_id": str(message.id),
                    "original_denier": denier_info,
                    "sync_time": datetime.utcnow().isoformat(),
                },
            )
            session.add(sync_log)
            session.commit()

        except Exception as e:
            logger.error(f"Error updating denied message {message.id}: {e}")
            self.stats["errors"] += 1

    async def trigger_manual_run(
        self, guild_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Trigger a manual sync run"""
        logger.info(f"Manual sync triggered for guild: {guild_id or 'all'}")

        # Store current stats
        before_stats = self.stats.copy()

        try:
            if guild_id:
                await self.sync_guild(guild_id)
            else:
                await self.sync_all_guilds()

            # Calculate changes
            return {
                "success": True,
                "messages_checked": self.stats["messages_checked"]
                - before_stats["messages_checked"],
                "messages_updated": self.stats["messages_updated"]
                - before_stats["messages_updated"],
                "errors": self.stats["errors"] - before_stats["errors"],
                "last_run": self.last_run.isoformat() if self.last_run else None,
            }
        except Exception as e:
            logger.error(f"Error in manual sync: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "messages_checked": 0,
                "messages_updated": 0,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics for the sync task"""
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "total_runs": self.stats["total_runs"],
            "total_messages_checked": self.stats["messages_checked"],
            "total_messages_updated": self.stats["messages_updated"],
            "total_errors": self.stats["errors"],
        }
