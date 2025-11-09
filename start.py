#!/usr/bin/env python3
"""Quick start script for Vela"""

import os
import sys
from pathlib import Path

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

    print("Checking prerequisites...")

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