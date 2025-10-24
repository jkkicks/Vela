"""Main Discord bot implementation with SQLModel integration"""
import discord
from discord.ext import commands
import os
import logging
import asyncio
from typing import Optional
from src.shared.config import settings, get_guild_settings, decrypt_value
from src.shared.database import init_database, get_session
from src.shared.models import Guild, Member, Channel
from sqlmodel import select

# Setup logging
logging.basicConfig(
    filename='sparkbot.log',
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SparkBot(commands.Bot):
    """Custom bot class with persistent views and database integration"""

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or("/"),
            intents=intents
        )
        self.guild_id: Optional[int] = None
        self.db_initialized = False

    async def setup_hook(self) -> None:
        """Setup persistent views and load cogs"""
        # Import and add persistent views
        from src.bot.views.onboarding import OnboardingView
        self.add_view(OnboardingView())

        # Load all cogs
        await self.load_cogs()
        logger.info("Bot setup completed")

    async def load_cogs(self):
        """Load all bot cogs"""
        cogs = [
            "src.bot.cogs.onboarding",
            "src.bot.cogs.admin",
            "src.bot.cogs.utilities"
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Logged in as {self.user}')
        print(f'Logged in as {self.user}')

        # Initialize database if not already done
        if not self.db_initialized:
            self.db_initialized = init_database()
            if not self.db_initialized:
                logger.warning("Database not initialized - first run setup required")
                print("⚠️ Database not initialized - please complete setup via web interface")
                return

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f'Slash Commands Synced. {len(synced)} Total Commands')
            print(f'Slash Commands Synced. {len(synced)} Total Commands')
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

        # Setup welcome messages for all guilds
        for guild in self.guilds:
            await self.setup_guild(guild)

        print("Bot is ready!")

    async def setup_guild(self, guild: discord.Guild):
        """Setup a guild with welcome message and configurations"""
        try:
            # Get guild configuration from database
            with next(get_session()) as session:
                db_guild = session.exec(
                    select(Guild).where(Guild.guild_id == guild.id)
                ).first()

                if not db_guild:
                    logger.warning(f"Guild {guild.id} not found in database")
                    return

                # Get welcome channel configuration
                welcome_channel = session.exec(
                    select(Channel).where(
                        Channel.guild_id == guild.id,
                        Channel.channel_type == "welcome",
                        Channel.enabled == True
                    )
                ).first()

                if welcome_channel:
                    await self.setup_welcome_message(guild, welcome_channel.channel_id)

        except Exception as e:
            logger.error(f"Error setting up guild {guild.id}: {e}")

    async def setup_welcome_message(self, guild: discord.Guild, channel_id: int):
        """Setup or verify welcome message in the specified channel"""
        channel = guild.get_channel(channel_id)
        if not channel:
            logger.warning(f"Welcome channel {channel_id} not found in guild {guild.id}")
            return

        # Check if welcome message already exists
        try:
            async for message in channel.history(limit=100):
                if message.author == self.user and message.embeds:
                    # Check if it's a welcome message
                    if message.embeds[0].title and "Welcome" in message.embeds[0].title:
                        logger.info(f'Welcome message found in {guild.name}. Message ID: {message.id}')
                        return

            # Create welcome message if not found
            from src.bot.views.onboarding import OnboardingView

            embed = discord.Embed(
                title="Welcome to the Server!",
                description="Here's how to get started:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Step 1:",
                value="Read the server rules in the rules channel."
            )
            embed.add_field(
                name="Step 2:",
                value="Check out some cool posts in the projects channel."
            )
            embed.add_field(
                name="Step 3:",
                value="Complete the Onboarding procedure to unlock the rest of the server."
            )
            embed.set_footer(text="Enjoy your stay!")

            await channel.send(embed=embed, view=OnboardingView())
            logger.info(f'Created welcome message in {guild.name}')

        except Exception as e:
            logger.error(f"Error setting up welcome message: {e}")

    async def on_member_join(self, member: discord.Member):
        """Handle new member joining"""
        try:
            with next(get_session()) as session:
                # Check if member already exists in database
                existing_member = session.exec(
                    select(Member).where(
                        Member.user_id == member.id,
                        Member.guild_id == member.guild.id
                    )
                ).first()

                if not existing_member:
                    # Add new member to database
                    new_member = Member(
                        user_id=member.id,
                        guild_id=member.guild.id,
                        username=member.name,
                        join_datetime=member.joined_at,
                        onboarding_status=0
                    )
                    session.add(new_member)
                    session.commit()
                    logger.info(f'Member {member.name} joined {member.guild.name}')
                else:
                    logger.info(f'Member {member.name} rejoined {member.guild.name}')

                # Ensure welcome message exists
                await self.setup_guild(member.guild)

        except Exception as e:
            logger.error(f"Error handling member join: {e}")

    async def on_member_remove(self, member: discord.Member):
        """Handle member leaving"""
        logger.info(f'Member {member.name} left {member.guild.name}')


async def run_bot():
    """Run the Discord bot"""
    bot = SparkBot()

    # Get bot token from database or environment
    token = None

    with next(get_session()) as session:
        # Try to get token from the first active guild
        guild = session.exec(
            select(Guild).where(Guild.is_active == True).limit(1)
        ).first()

        if guild and guild.bot_token:
            try:
                token = decrypt_value(guild.bot_token)
            except Exception:
                # Fall back to environment variable if decryption fails
                token = settings.bot_token

    if not token:
        token = settings.bot_token

    if not token:
        logger.error("No bot token configured. Please set BOT_TOKEN in .env or configure via web interface")
        print("❌ No bot token configured. Please set BOT_TOKEN in .env or configure via web interface")
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