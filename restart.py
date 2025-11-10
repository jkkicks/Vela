#!/usr/bin/env python3
"""
Restart script that kills any existing process on port 8000 before starting
"""

import subprocess
import sys
import time

print("🔄 Restarting Vela...\n")

# Kill any existing process on port 8000
print("🔍 Checking for existing processes...")
result = subprocess.run([sys.executable, "kill_port_8000.py"])

if result.returncode == 0:
    # Give a moment for ports to be released
    time.sleep(1)

    print("\n🚀 Starting Vela...\n")
    print("-" * 50)

    try:
        # Start Vela with proper process management
        subprocess.run([sys.executable, "start.py"])
    except KeyboardInterrupt:
        print("\n\nRestart cancelled by user")
        sys.exit(0)
else:
    print("\n❌ Failed to clean up existing processes")
    print("You may need to manually kill Python processes:")
    print("  Windows: taskkill /F /IM python.exe")
    print("  Linux/Mac: killall python3")
    sys.exit(1)
