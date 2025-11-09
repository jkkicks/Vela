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

from src.bot.main import VelaBot
from src.api.main import app
from src.shared.config import settings
from src.shared.database import init_database, get_session
from src.shared.models import Guild, AdminUser
from sqlmodel import select

# Custom logging filter to suppress expected CancelledError during shutdown
class SuppressCancelledErrorFilter(logging.Filter):
    def filter(self, record):
        # Suppress CancelledError tracebacks from starlette/uvicorn during shutdown
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type and exc_type.__name__ == 'CancelledError':
                return False
        return True

# Setup logging - default to ./data unless overridden
data_dir = os.getenv('DATA_DIR', './data')
os.makedirs(data_dir, exist_ok=True)

log_file = os.getenv('LOG_FILE', os.path.join(data_dir, 'vela.log'))

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add filter to uvicorn and starlette loggers to suppress CancelledError
for logger_name in ['uvicorn.error', 'uvicorn', 'starlette']:
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
            guild = session.exec(
                select(Guild).where(Guild.is_active == True).limit(1)
            ).first()

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
            logger.info("No valid bot token configured. Bot will not start until setup is complete.")
            return

        logger.info("Starting Discord bot...")
        await bot.start(token)

    except asyncio.CancelledError:
        logger.info("Bot task cancelled, closing bot...")
        if bot_instance and not bot_instance.is_closed():
            await bot_instance.close()
        raise
    except discord.LoginFailure as e:
        logger.error(f"Failed to login to Discord: Invalid token")
        print(f"❌ Failed to start Discord bot: Invalid or improper token")
        print(f"   Please configure a valid bot token via the setup interface")
        # Don't raise - allow the application to continue running
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"❌ Discord bot error: {e}")
        # Don't raise - allow the application to continue running


async def run_api():
    """Run the FastAPI server"""
    server = None
    try:
        logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")

        config = uvicorn.Config(
            app="src.api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            reload=settings.debug
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


async def shutdown(tasks, signal_name="SIGINT"):
    """Gracefully shutdown all tasks"""
    logger.info(f"Received {signal_name}, shutting down...")
    print(f"\n🛑 Shutting down Vela...")

    # Cancel all tasks
    for task in tasks:
        if not task.done():
            task.cancel()

    # Wait for tasks to be cancelled (with timeout)
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        logger.warning("Some tasks did not complete within timeout")

    # Cleanup bot instance
    global bot_instance
    if bot_instance and not bot_instance.is_closed():
        try:
            await asyncio.wait_for(bot_instance.close(), timeout=3.0)
            print("✅ Discord bot stopped")
        except asyncio.TimeoutError:
            logger.warning("Bot close timed out")
        except Exception as e:
            logger.error(f"Error closing bot: {e}")

    print("✅ Web server stopped")


async def main():
    """Run both services concurrently"""
    print("""
    ╔═══════════════════════════════════════╗
    ║           Vela v2.0.0                 ║
    ║  Discord Onboarding Bot with Web UI   ║
    ╚═══════════════════════════════════════╝
    """)

    # Initialize database
    logger.info("Initializing database...")
    is_initialized = init_database()

    # Check if setup has been completed (admin user exists)
    setup_completed = False
    with next(get_session()) as session:
        admin_exists = session.exec(select(AdminUser).limit(1)).first()
        setup_completed = admin_exists is not None

    if not setup_completed:
        print("\n⚠️  First-run setup required!")
        print(f"Please visit http://localhost:{settings.api_port}/setup to complete initial configuration\n")

    # Create tasks for both services
    tasks = []

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

    print(f"\n✅ Web interface available at: http://localhost:{settings.api_port}")
    print(f"📚 API documentation at: http://localhost:{settings.api_port}/docs\n")
    print("Press Ctrl+C to stop\n")

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def handle_shutdown():
        asyncio.create_task(shutdown(tasks))

    # On Windows, only SIGINT is available
    try:
        loop.add_signal_handler(signal.SIGINT, handle_shutdown)
    except (NotImplementedError, AttributeError):
        # Windows doesn't support add_signal_handler
        # Will rely on KeyboardInterrupt exception instead
        pass

    # Run both services with proper shutdown handling
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await shutdown(tasks, "KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        await shutdown(tasks, "Exception")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Shutdown already handled in main()
        print("👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)