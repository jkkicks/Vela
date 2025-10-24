"""Main entry point for running both Discord bot and FastAPI server"""
import asyncio
import logging
import os
import sys
import signal
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.main import SparkBot
from src.api.main import app
from src.shared.config import settings
from src.shared.database import init_database, get_session
from src.shared.models import Guild
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

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sparkbot.log'),
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
        bot = SparkBot()
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
                except Exception:
                    # Fall back to environment variable if decryption fails
                    token = settings.bot_token

        if not token:
            token = settings.bot_token

        if not token:
            logger.warning("No bot token configured. Bot will not start.")
            logger.info("Please configure the bot via the web interface at http://localhost:8000")
            return

        logger.info("Starting Discord bot...")
        await bot.start(token)

    except asyncio.CancelledError:
        logger.info("Bot task cancelled, closing bot...")
        if bot_instance and not bot_instance.is_closed():
            await bot_instance.close()
        raise
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise


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
    print(f"\n🛑 Shutting down SparkBot...")

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
    ║         SparkBot v2.0.0               ║
    ║  Discord Onboarding Bot with Web UI   ║
    ╚═══════════════════════════════════════╝
    """)

    # Initialize database
    logger.info("Initializing database...")
    is_initialized = init_database()

    if not is_initialized:
        print("\n⚠️  First-run setup required!")
        print(f"Please visit http://localhost:{settings.api_port}/setup to complete initial configuration\n")

    # Create tasks for both services
    tasks = []

    # Always start the API
    api_task = asyncio.create_task(run_api())
    tasks.append(api_task)

    # Only start bot if configured
    bot_task = None
    if is_initialized or settings.bot_token:
        bot_task = asyncio.create_task(run_bot())
        tasks.append(bot_task)

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