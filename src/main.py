"""Main entry point for running both Discord bot and FastAPI server"""

import asyncio
import logging
import os
import sys
import signal
import uvicorn
import discord
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.main import VelaBot  # noqa: E402
from src.shared.config import settings  # noqa: E402
from src.shared.database import init_database, get_session  # noqa: E402
from src.shared.models import Guild, AdminUser  # noqa: E402
from sqlmodel import select  # noqa: E402


# Custom logging filter to suppress expected CancelledError during shutdown
class SuppressCancelledErrorFilter(logging.Filter):
    def filter(self, record):
        # Suppress CancelledError tracebacks from starlette/uvicorn during shutdown
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type and exc_type.__name__ == "CancelledError":
                return False
        return True


# Setup logging - default to ./data unless overridden
data_dir = os.getenv("DATA_DIR", "./data")
os.makedirs(data_dir, exist_ok=True)

log_file = os.getenv("LOG_FILE", os.path.join(data_dir, "vela.log"))

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Add filter to uvicorn and starlette loggers to suppress CancelledError
for logger_name in ["uvicorn.error", "uvicorn", "starlette"]:
    log = logging.getLogger(logger_name)
    log.addFilter(SuppressCancelledErrorFilter())

# Global bot instance for API access
bot_instance = None


async def run_bot():
    global bot_instance
    """Run the Discord bot"""
    try:
        bot = VelaBot()
        bot_instance = bot  # Make bot accessible to API

        # Also attach to the FastAPI app so it's accessible from routers
        from src.api.main import app as fastapi_app

        fastapi_app.state.bot = bot

        # Get bot token from database or environment
        token = None
        with next(get_session()) as session:
            # Try to get token from the first active guild
            guild = session.exec(select(Guild).where(Guild.is_active).limit(1)).first()

            if guild and guild.bot_token:
                try:
                    from src.shared.config import decrypt_value

                    token = decrypt_value(guild.bot_token)
                except Exception as e:
                    logger.warning(f"Failed to decrypt token from database: {e}")
                    # Fall back to environment variable if decryption fails
                    token = settings.bot_token

        if not token:
            token = settings.bot_token

        if not token or token == "your_bot_token_here":
            logger.info(
                "No valid bot token configured. Bot will not start until setup is complete."
            )
            return

        logger.info("Starting Discord bot...")
        await bot.start(token)

    except asyncio.CancelledError:
        logger.info("Bot task cancelled, closing bot...")
        if bot_instance and not bot_instance.is_closed():
            await bot_instance.close()
        raise
    except discord.LoginFailure:
        logger.error("Failed to login to Discord: Invalid token")
        print("[ERROR] Failed to start Discord bot: Invalid or improper token")
        print("   Please configure a valid bot token via the setup interface")
        # Don't raise - allow the application to continue running
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"[ERROR] Discord bot error: {e}")
        # Don't raise - allow the application to continue running


async def run_api():
    """Run the FastAPI server"""
    server = None
    try:
        logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")

        # Import app directly to ensure lifespan runs immediately
        from src.api.main import app

        config = uvicorn.Config(
            app=app,
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            reload=settings.debug,
        )
        server = uvicorn.Server(config)

        # Override uvicorn's signal handlers so we can handle shutdown ourselves
        server.install_signal_handlers = lambda: None

        await server.serve()

    except asyncio.CancelledError:
        logger.info("API server task cancelled, shutting down...")
        if server:
            server.should_exit = True
        raise
    except Exception as e:
        logger.error(f"API error: {e}")
        raise




async def main():
    """Run both services concurrently"""
    print(
        """
    ========================================
               Vela v2.0.0
      Discord Onboarding Bot with Web UI
    ========================================
    """
    )

    # Initialize database
    logger.info("Initializing database...")
    init_database()

    # Check if setup has been completed (admin user exists)
    setup_completed = False
    with next(get_session()) as session:
        admin_exists = session.exec(select(AdminUser).limit(1)).first()
        setup_completed = admin_exists is not None

    if not setup_completed:
        print("\n[WARNING] First-run setup required!")
        print(
            f"Please visit http://localhost:{settings.api_port}/setup to complete initial configuration\n"
        )

    # Create tasks for both services
    tasks = []
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    # Signal handler to trigger shutdown
    def signal_handler():
        """Handle shutdown signals"""
        logger.info("Received shutdown signal")
        shutdown_event.set()
        # Cancel all tasks
        for task in asyncio.all_tasks(loop):
            task.cancel()

    # Register signal handlers based on platform
    if sys.platform == 'win32':
        # Windows signal handling
        signal.signal(signal.SIGBREAK, lambda s, f: signal_handler())
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    else:
        # Unix signal handling
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
        loop.add_signal_handler(signal.SIGINT, signal_handler)

    # Always start the API
    api_task = asyncio.create_task(run_api())
    tasks.append(api_task)

    # Only start bot if setup is completed
    bot_task = None
    if setup_completed:
        bot_task = asyncio.create_task(run_bot())
        tasks.append(bot_task)
    else:
        logger.info("Skipping Discord bot startup - setup not completed")

    print(f"\n[OK] Web interface available at: http://localhost:{settings.api_port}")
    print(f"[INFO] API documentation at: http://localhost:{settings.api_port}/docs\n")
    print("Press Ctrl+C to stop\n")

    # Run both services
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nShutting down...")
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        # Wait for tasks to cancel
        await asyncio.gather(*tasks, return_exceptions=True)

        # Close bot if needed
        if bot_instance and not bot_instance.is_closed():
            await bot_instance.close()

        print("Shutdown complete")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Fatal error: {e}")
        sys.exit(1)
