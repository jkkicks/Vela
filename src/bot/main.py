"""Main Discord bot implementation with SQLModel integration"""

import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional
from src.shared.config import settings, decrypt_value
from src.shared.database import init_database, get_session
from src.shared.models import Guild, Member
from sqlmodel import select

# Setup logging
logging.basicConfig(
    filename="vela.log",
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VelaBot(commands.Bot):
    """Custom bot class with persistent views and database integration"""

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or("/"), intents=intents
        )
        self.guild_id: Optional[int] = None
        self.db_initialized = False

    async def setup_hook(self) -> None:
        """Setup persistent views and load cogs"""
        # Import and add persistent views
        from src.bot.views.onboarding import OnboardingView, OnboardingApprovalView

        self.add_view(OnboardingView())
        self.add_view(
            OnboardingApprovalView()
        )  # Add approval view for persistent handling

        # Load all cogs
        await self.load_cogs()
        logger.info("Bot setup completed")

    async def load_cogs(self):
        """Load all bot cogs"""
        cogs = [
            "src.bot.cogs.onboarding",
            "src.bot.cogs.admin",
            "src.bot.cogs.utilities",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as {self.user}")
        print(f"Logged in as {self.user}")

        # Initialize database if not already done
        if not self.db_initialized:
            self.db_initialized = init_database()
            if not self.db_initialized:
                logger.warning("Database not initialized - first run setup required")
                print(
                    "⚠️ Database not initialized - please complete setup via web interface"
                )
                return

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Slash Commands Synced. {len(synced)} Total Commands")
            print(f"Slash Commands Synced. {len(synced)} Total Commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

        print("Bot is ready!")

    def _get_welcome_message_content(self, welcome_config: dict, guild_id: int):
        """Build welcome message content from configuration"""
        from src.bot.views.onboarding import OnboardingView

        message_type = welcome_config.get("type", "embed")
        view = OnboardingView(guild_id=guild_id)

        # Default configuration
        default_config = {
            "title": "Welcome to the Server!",
            "description": "Here's how to get started:",
            "color": "green",
            "fields": [
                {
                    "name": "Step 1:",
                    "value": "Read the server rules in the rules channel.",
                    "inline": False,
                },
                {
                    "name": "Step 2:",
                    "value": "Check out some cool posts in the projects channel.",
                    "inline": False,
                },
                {
                    "name": "Step 3:",
                    "value": "Complete the Onboarding procedure to unlock the rest of the server.",
                    "inline": False,
                },
            ],
            "footer": "Enjoy your stay!",
        }

        if message_type == "plain":
            # Plain text message
            content = welcome_config.get(
                "content",
                "Welcome to the Server!\n\nHere's how to get started:\n\nStep 1: Read the server rules in the rules channel.\nStep 2: Check out some cool posts in the projects channel.\nStep 3: Complete the Onboarding procedure to unlock the rest of the server.\n\nEnjoy your stay!",
            )
            return {"content": content, "embed": None, "view": view}
        else:
            # Embed message
            embed_config = welcome_config.get("embed", default_config)

            # Parse color
            color_value = embed_config.get("color", "green")
            if isinstance(color_value, str):
                color_map = {
                    "red": discord.Color.red(),
                    "green": discord.Color.green(),
                    "blue": discord.Color.blue(),
                    "yellow": discord.Color.gold(),
                    "purple": discord.Color.purple(),
                    "orange": discord.Color.orange(),
                }
                color = color_map.get(color_value.lower(), discord.Color.green())
            else:
                color = discord.Color(color_value)

            embed = discord.Embed(
                title=embed_config.get("title", default_config["title"]),
                description=embed_config.get(
                    "description", default_config["description"]
                ),
                color=color,
            )

            # Add fields
            fields = embed_config.get("fields", default_config["fields"])
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False),
                )

            # Add footer
            footer = embed_config.get("footer", default_config["footer"])
            if footer:
                embed.set_footer(text=footer)

            return {"content": None, "embed": embed, "view": view}

    async def create_welcome_message(
        self, guild_id: int, channel_id: int
    ) -> tuple[bool, str, Optional[int]]:
        """Create a new welcome message in the channel"""
        try:
            guild = self.get_guild(guild_id)
            if not guild:
                return False, "Guild not found", None

            channel = guild.get_channel(channel_id)
            if not channel:
                return False, "Channel not found", None

            # Get guild configuration from database
            with next(get_session()) as session:
                db_guild = session.exec(
                    select(Guild).where(Guild.guild_id == guild_id)
                ).first()

                if not db_guild:
                    return False, "Guild not found in database", None

                # Get welcome message configuration
                welcome_config = db_guild.settings.get("welcome_message_config", {})

            # Build message content
            msg_data = self._get_welcome_message_content(welcome_config, guild_id)

            # Send message
            if msg_data["embed"]:
                message = await channel.send(
                    embed=msg_data["embed"], view=msg_data["view"]
                )
            else:
                message = await channel.send(
                    content=msg_data["content"], view=msg_data["view"]
                )

            logger.info(f"Created welcome message in {guild.name} (ID: {message.id})")
            return True, "Welcome message created successfully", message.id

        except Exception as e:
            logger.error(f"Error creating welcome message: {e}")
            return False, str(e), None

    async def update_welcome_message(
        self, guild_id: int, channel_id: int, message_id: int
    ) -> tuple[bool, str]:
        """Update an existing welcome message"""
        try:
            guild = self.get_guild(guild_id)
            if not guild:
                return False, "Guild not found"

            channel = guild.get_channel(channel_id)
            if not channel:
                return False, "Channel not found"

            # Get the message
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                return False, "Welcome message not found - it may have been deleted"
            except discord.Forbidden:
                return False, "Bot doesn't have permission to access this message"

            # Get guild configuration
            with next(get_session()) as session:
                db_guild = session.exec(
                    select(Guild).where(Guild.guild_id == guild_id)
                ).first()

                if not db_guild:
                    return False, "Guild not found in database"

                welcome_config = db_guild.settings.get("welcome_message_config", {})

            # Build message content
            msg_data = self._get_welcome_message_content(welcome_config, guild_id)

            # Update message
            if msg_data["embed"]:
                await message.edit(
                    content=None, embed=msg_data["embed"], view=msg_data["view"]
                )
            else:
                await message.edit(
                    content=msg_data["content"], embed=None, view=msg_data["view"]
                )

            logger.info(f"Updated welcome message in {guild.name} (ID: {message_id})")
            return True, "Welcome message updated successfully"

        except Exception as e:
            logger.error(f"Error updating welcome message: {e}")
            return False, str(e)

    async def replace_welcome_message(
        self, guild_id: int, channel_id: int, old_message_id: Optional[int]
    ) -> tuple[bool, str, Optional[int]]:
        """Delete the old message and create a new one"""
        try:
            guild = self.get_guild(guild_id)
            if not guild:
                return False, "Guild not found", None

            channel = guild.get_channel(channel_id)
            if not channel:
                return False, "Channel not found", None

            # Delete old message if it exists
            if old_message_id:
                try:
                    old_message = await channel.fetch_message(old_message_id)
                    await old_message.delete()
                    logger.info(f"Deleted old welcome message (ID: {old_message_id})")
                except discord.NotFound:
                    logger.warning(
                        f"Old welcome message not found (ID: {old_message_id})"
                    )
                except discord.Forbidden:
                    return (
                        False,
                        "Bot doesn't have permission to delete the old message",
                        None,
                    )

            # Create new message
            success, message, new_message_id = await self.create_welcome_message(
                guild_id, channel_id
            )

            if success:
                return True, "Welcome message replaced successfully", new_message_id
            else:
                return False, f"Failed to create new message: {message}", None

        except Exception as e:
            logger.error(f"Error replacing welcome message: {e}")
            return False, str(e), None

    async def on_member_join(self, member: discord.Member):
        """Handle new member joining"""
        try:
            with next(get_session()) as session:
                # Check if member already exists in database
                existing_member = session.exec(
                    select(Member).where(
                        Member.user_id == member.id, Member.guild_id == member.guild.id
                    )
                ).first()

                if not existing_member:
                    # Add new member to database
                    new_member = Member(
                        user_id=member.id,
                        guild_id=member.guild.id,
                        username=member.name,
                        join_datetime=member.joined_at,
                        onboarding_status=0,
                    )
                    session.add(new_member)
                    session.commit()
                    logger.info(f"Member {member.name} joined {member.guild.name}")
                else:
                    logger.info(f"Member {member.name} rejoined {member.guild.name}")

        except Exception as e:
            logger.error(f"Error handling member join: {e}")

    async def on_member_remove(self, member: discord.Member):
        """Handle member leaving"""
        logger.info(f"Member {member.name} left {member.guild.name}")


async def run_bot():
    """Run the Discord bot"""
    bot = VelaBot()

    # Get bot token from database or environment
    token = None

    with next(get_session()) as session:
        # Try to get token from the first active guild
        guild = session.exec(select(Guild).where(Guild.is_active).limit(1)).first()

        if guild and guild.bot_token:
            try:
                token = decrypt_value(guild.bot_token)
            except Exception:
                # Fall back to environment variable if decryption fails
                token = settings.bot_token

    if not token:
        token = settings.bot_token

    if not token:
        logger.error(
            "No bot token configured. Please set BOT_TOKEN in .env or configure via web interface"
        )
        print(
            "❌ No bot token configured. Please set BOT_TOKEN in .env or configure via web interface"
        )
        return

    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token")
        print("❌ Invalid bot token")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"❌ Bot error: {e}")


def main():
    """Main entry point for the bot"""
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
