#!/usr/bin/env python3
"""
Vela Restart Script
===================

Safely restarts Vela by killing existing processes first.

Usage: python restart.py

What this script does:
1. Finds all running Vela processes (on port 8000 or running src.main)
2. Gracefully terminates them
3. Waits for ports to be released
4. Starts Vela fresh with start.py

Why we need this script:
- Prevents "port already in use" errors
- Ensures clean restart without manual process management
- Useful during development when you need to restart frequently
- Cross-platform (Windows, Linux, macOS)

When to use this:
- During development when you make code changes
- When Vela gets stuck or unresponsive
- Alternative to manually stopping and starting
"""

import subprocess
import sys
import time
import psutil
import os


def kill_vela_processes():
    """Find and kill all Vela processes"""
    print("🔍 Looking for existing Vela processes...")

    current_pid = os.getpid()
    killed_count = 0
    vela_processes = []

    # Find all Python processes running Vela
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            # Skip current process
            if proc.info["pid"] == current_pid:
                continue

            # Check if it's a Python process running Vela
            if proc.info["name"] and "python" in proc.info["name"].lower():
                cmdline = proc.info.get("cmdline", [])
                if cmdline and any(
                    "start.py" in arg or "src.main" in arg for arg in cmdline
                ):
                    vela_processes.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not vela_processes:
        print("✅ No existing Vela processes found")
        return True

    print(f"📋 Found {len(vela_processes)} Vela process(es)")

    # Try graceful shutdown first
    for proc in vela_processes:
        try:
            print(f"   Terminating PID {proc.pid}...")
            proc.terminate()
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Wait for graceful shutdown
    gone, alive = psutil.wait_procs(vela_processes, timeout=3)

    # Force kill if still running
    if alive:
        print("   Force killing remaining processes...")
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    print(f"✅ Stopped {killed_count} process(es)")
    return True


def main():
    print("=" * 60)
    print("🔄 Restarting Vela...")
    print("=" * 60)
    print()

    # Kill existing processes
    if not kill_vela_processes():
        print("\n❌ Failed to clean up existing processes")
        print("You may need to manually kill Python processes")
        sys.exit(1)

    # Give a moment for ports to be released
    print("\n⏳ Waiting for ports to be released...")
    time.sleep(2)

    print("\n🚀 Starting Vela...\n")
    print("-" * 60)

    try:
        # Start Vela with proper process management
        subprocess.run([sys.executable, "start.py"])
    except KeyboardInterrupt:
        print("\n\n🛑 Restart cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting Vela: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
