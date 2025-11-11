# Vela Shutdown Handling Documentation

## Overview
This document explains how Vela handles graceful shutdown in both local development and Docker production environments.

## Local Development (start.py)

### How it Works
1. `start.py` is a simple wrapper for local development
2. Uses `subprocess.run()` to launch `src.main`
3. Both processes receive Ctrl+C signal on Windows
4. Python's subprocess module handles signal propagation properly

### Key Features
- Automatic virtual environment detection and activation
- Environment file validation
- Static asset checking
- Clean process termination

## Production (Docker)

### Signal Handling
1. **Tini** is used as the init system for proper signal handling
2. `PYTHONUNBUFFERED=1` ensures real-time log output
3. `SIGTERM` is the stop signal with 10s grace period
4. Application handles shutdown gracefully

### Docker Configuration
```dockerfile
# Use tini for proper signal handling
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "src.main"]
```

## src/main.py Implementation

### Graceful Shutdown Process
1. **Signal Reception**: Application receives SIGINT (Ctrl+C) or SIGTERM (Docker)
2. **Task Cancellation**: All async tasks are cancelled
3. **Cleanup**: Discord bot connection closed, API server stopped
4. **Timeout**: 5-second timeout for graceful shutdown
5. **Exit**: Clean exit with proper logging

### Key Functions
- `graceful_shutdown(tasks)`: Handles the shutdown sequence
- `run_bot()`: Manages Discord bot lifecycle
- `run_api()`: Manages FastAPI server lifecycle

## Best Practices

### Production Readiness
- ✅ Unbuffered output (`PYTHONUNBUFFERED=1`)
- ✅ Proper signal handling for containers
- ✅ Graceful shutdown with timeout
- ✅ Comprehensive error logging
- ✅ Clean resource cleanup

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Stop gracefully
docker-compose down

# View logs
docker-compose logs -f app
```

### Local Development
```bash
# Run locally
python start.py

# Stop with Ctrl+C
# Application shuts down gracefully
```

## Troubleshooting

### Windows Terminal Issues
- If Ctrl+C appears in wrong place: Terminal buffering issue, not application problem
- Solution: Reset terminal or use `cls` command

### Docker Shutdown Issues
- Ensure `tini` is installed in container
- Check `stop_grace_period` in docker-compose.yml
- Verify `PYTHONUNBUFFERED=1` is set

### Signal Handling
- Windows: Uses KeyboardInterrupt exception
- Unix/Docker: Uses asyncio signal handlers
- Both approaches ensure graceful shutdown

## Testing Shutdown

### Local Test
1. Run `python start.py`
2. Wait for "Bot is ready!" message
3. Press Ctrl+C
4. Verify clean shutdown messages

### Docker Test
1. Run `docker-compose up`
2. In another terminal: `docker-compose stop`
3. Verify graceful shutdown in logs
4. Check exit code: `docker-compose ps`

## Summary
The implementation provides robust, production-ready shutdown handling that works consistently across local development and Docker deployments. The code is clean, maintainable, and follows Python best practices.