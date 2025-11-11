#!/usr/bin/env python3
# fmt: off
"""Quick start script for Vela"""

import os
import sys
import subprocess
import signal
import atexit
from pathlib import Path

def is_venv():
    """Check if currently running in a virtual environment"""
    return (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
        os.environ.get('VIRTUAL_ENV') is not None
    )

def verify_venv_python_version(venv_python):
    """Verify the venv is using Python 3.13"""
    try:
        result = subprocess.run(
            [str(venv_python), '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()

        if '3.13' not in version:
            return False, version
        return True, version
    except Exception:
        return False, "Unknown"


def check_venv():
    """Check if venv exists and use it automatically"""
    venv_path = Path('.venv')

    # If already in a venv, we're good
    if is_venv():
        print("[OK] Running in virtual environment")
        return True

    print("Checking virtual environment...")

    # Determine the path to the venv python
    if sys.platform == 'win32':
        venv_python = venv_path / 'Scripts' / 'python.exe'
    else:
        venv_python = venv_path / 'bin' / 'python'

    # Check if .venv exists
    if not venv_path.exists() or not venv_python.exists():
        print("[ERROR] Virtual environment not found!")
        print("\nPlease run the setup script first:")
        print("  python setup_venv.py")
        return False

    print("[OK] Virtual environment found at .venv/")

    # Verify Python version
    is_correct_version, version = verify_venv_python_version(venv_python)

    if not is_correct_version:
        print(f"[WARNING] Wrong Python version in venv: {version}")
        print("Expected: Python 3.13.x")
        print("\nPlease recreate the virtual environment:")
        print("  python setup_venv.py")
        return False

    print(f"[OK] Using {version}")

    # Re-execute this script in the venv
    print("\nRestarting in virtual environment...\n")
    print("-" * 50)
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

def check_env():
    """Check if .env file exists and has minimum configuration"""
    env_path = Path(".env")

    if not env_path.exists():
        print("[ERROR] .env file not found!")
        print("\nCreating .env from .env.example...")

        example_path = Path(".env.example")
        if example_path.exists():
            env_path.write_text(example_path.read_text())
            print("[OK] Created .env file. Please edit it with your configuration.")
        else:
            print("[ERROR] .env.example not found either!")
            return False

    # Check if encryption key exists
    env_content = env_path.read_text()
    if "ENCRYPTION_KEY=" not in env_content or "ENCRYPTION_KEY=\n" in env_content or "ENCRYPTION_KEY=$" in env_content:
        print("\n[WARNING] ENCRYPTION_KEY not set in .env")
        print("Generating encryption key...")

        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()

        # Add or update encryption key in .env
        lines = env_content.split('\n')
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith('ENCRYPTION_KEY='):
                lines[i] = f'ENCRYPTION_KEY={key}'
                key_found = True
                break

        if not key_found:
            lines.append(f'ENCRYPTION_KEY={key}')

        env_path.write_text('\n'.join(lines))
        print(f"[OK] Added ENCRYPTION_KEY to .env")

    return True

def check_static_assets():
    """Check if static assets are downloaded"""
    static_dir = Path("static")
    htmx_file = static_dir / "htmx.min.js"

    if not htmx_file.exists():
        print("\nDownloading static assets...")
        os.system("python download_assets.py")
    else:
        print("[OK] Static assets already downloaded")

def main():
    print("""
========================================
           Vela v2.0 Startup
  Discord Onboarding Bot with Web UI
========================================
    """)

    print("Checking prerequisites...\n")

    # Check and setup virtual environment (will re-execute if needed)
    check_venv()

    # Check environment
    if not check_env():
        print("\n[ERROR] Please configure your .env file and try again.")
        sys.exit(1)

    # Check static assets
    check_static_assets()

    print("\n[OK] All checks passed!")
    print("\nStarting Vela...")
    print("-" * 40)

    # Start the application with proper process management
    process = None

    def cleanup_process():
        """Cleanup function to ensure the process is terminated"""
        nonlocal process
        if process and process.poll() is None:
            if sys.platform == 'win32':
                # On Windows, use taskkill to force kill the process tree
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                             capture_output=True, check=False)
            else:
                # On Unix, terminate the process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except:
                    process.terminate()

            # Give it a moment to terminate
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def signal_handler(signum, frame):
        """Handle Ctrl+C and other signals"""
        print("\n\nReceived shutdown signal...")
        cleanup_process()
        sys.exit(0)

    # Register signal handlers
    if sys.platform == 'win32':
        # Windows signal handling
        signal.signal(signal.SIGBREAK, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    else:
        # Unix signal handling
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    # Register cleanup on exit
    atexit.register(cleanup_process)

    try:
        # Use subprocess.Popen for better process control
        if sys.platform == 'win32':
            # On Windows, don't create a new process group to allow Ctrl+C to work
            process = subprocess.Popen(
                [sys.executable, '-m', 'src.main']
            )
        else:
            # On Unix, create a new process group
            process = subprocess.Popen(
                [sys.executable, '-m', 'src.main'],
                preexec_fn=os.setsid
            )

        # Wait for the process to complete
        process.wait()

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        cleanup_process()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        cleanup_process()
        sys.exit(1)
    finally:
        cleanup_process()

if __name__ == "__main__":
    main()