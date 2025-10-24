#!/usr/bin/env python3
"""Test script to verify SparkBot installation"""

import sys
print("Testing SparkBot installation...")

try:
    # Test core imports
    import discord
    print("[OK] discord.py imported")

    import fastapi
    print("[OK] FastAPI imported")

    import sqlmodel
    print("[OK] SQLModel imported")

    # Test our modules
    from src.shared.models import Guild, Member
    print("[OK] Database models imported")

    from src.shared.config import settings
    print("[OK] Configuration imported")

    print("\n✅ All core dependencies installed successfully!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and configure it")
    print("2. Run: python download_assets.py")
    print("3. Run: python -m src.main")
    print("4. Visit http://localhost:8000/setup for initial configuration")

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)