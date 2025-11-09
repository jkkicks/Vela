#!/usr/bin/env python3
"""Quick start script for Vela"""

import os
import sys
import subprocess
from pathlib import Path

def is_venv():
    """Check if currently running in a virtual environment"""
    return (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
        os.environ.get('VIRTUAL_ENV') is not None
    )

def check_venv():
    """Check if venv exists and create/activate if needed"""
    venv_path = Path('.venv')

    # If already in a venv, we're good
    if is_venv():
        print("✅ Running in virtual environment")
        return True

    print("📦 Checking virtual environment...")

    # Check if .venv exists
    if venv_path.exists():
        print("✅ Virtual environment found at .venv/")
    else:
        print("🔨 Creating virtual environment at .venv/...")
        try:
            import venv
            venv.create('.venv', with_pip=True)
            print("✅ Virtual environment created")
        except Exception as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False

    # Determine the path to the venv python
    if sys.platform == 'win32':
        venv_python = venv_path / 'Scripts' / 'python.exe'
        venv_pip = venv_path / 'Scripts' / 'pip.exe'
    else:
        venv_python = venv_path / 'bin' / 'python'
        venv_pip = venv_path / 'bin' / 'pip'

    # Check if dependencies are installed
    print("📦 Checking dependencies...")
    try:
        result = subprocess.run(
            [str(venv_pip), 'show', 'fastapi'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Dependencies not installed
            print("📥 Installing dependencies (this may take a minute)...")
            install_result = subprocess.run(
                [str(venv_pip), 'install', '-r', 'requirements.txt'],
                capture_output=False  # Show output to user
            )

            if install_result.returncode != 0:
                print("❌ Failed to install dependencies")
                return False

            print("✅ Dependencies installed")
        else:
            print("✅ Dependencies already installed")
    except Exception as e:
        print(f"⚠️  Could not verify dependencies: {e}")

    # Re-execute this script in the venv
    print("\n🔄 Restarting in virtual environment...\n")
    print("-" * 50)
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

def check_env():
    """Check if .env file exists and has minimum configuration"""
    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env file not found!")
        print("\nCreating .env from .env.example...")

        example_path = Path(".env.example")
        if example_path.exists():
            env_path.write_text(example_path.read_text())
            print("✅ Created .env file. Please edit it with your configuration.")
        else:
            print("❌ .env.example not found either!")
            return False

    # Check if encryption key exists
    env_content = env_path.read_text()
    if "ENCRYPTION_KEY=" not in env_content or "ENCRYPTION_KEY=\n" in env_content or "ENCRYPTION_KEY=$" in env_content:
        print("\n⚠️  ENCRYPTION_KEY not set in .env")
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
        print(f"✅ Added ENCRYPTION_KEY to .env")

    return True

def check_static_assets():
    """Check if static assets are downloaded"""
    static_dir = Path("static")
    htmx_file = static_dir / "htmx.min.js"

    if not htmx_file.exists():
        print("\n📦 Downloading static assets...")
        os.system("python download_assets.py")
    else:
        print("✅ Static assets already downloaded")

def main():
    print("""
╔═══════════════════════════════════════╗
║           Vela v2.0 Startup           ║
║  Discord Onboarding Bot with Web UI   ║
╚═══════════════════════════════════════╝
    """)

    print("Checking prerequisites...\n")

    # Check and setup virtual environment (will re-execute if needed)
    check_venv()

    # Check environment
    if not check_env():
        print("\n❌ Please configure your .env file and try again.")
        sys.exit(1)

    # Check static assets
    check_static_assets()

    print("\n✅ All checks passed!")
    print("\nStarting Vela...")
    print("-" * 40)

    # Start the application
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "src.main"])
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n✅ Vela stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Vela startup cancelled")
        sys.exit(0)