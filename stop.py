"""Helper script to properly stop SparkBot"""
import psutil
import os
import sys
import time


def stop_sparkbot():
    """Find and stop all SparkBot processes"""
    print("🔍 Looking for SparkBot processes...")

    current_pid = os.getpid()
    killed_count = 0
    sparkbot_processes = []

    # Find all Python processes running SparkBot
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip current process
            if proc.info['pid'] == current_pid:
                continue

            # Check if it's a Python process
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('start.py' in arg or 'src.main' in arg or 'SparkBot' in str(arg) for arg in cmdline):
                    sparkbot_processes.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not sparkbot_processes:
        print("✅ No SparkBot processes found running")
        return

    print(f"\n📋 Found {len(sparkbot_processes)} SparkBot process(es):\n")

    for proc in sparkbot_processes:
        try:
            cmdline = ' '.join(proc.cmdline())
            print(f"   PID {proc.pid}: {cmdline[:80]}...")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("\n🛑 Stopping processes...\n")

    # Try graceful shutdown first
    for proc in sparkbot_processes:
        try:
            print(f"   Sending terminate signal to PID {proc.pid}...")
            proc.terminate()
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"   ⚠️  Could not terminate PID {proc.pid}: {e}")

    # Wait for graceful shutdown
    gone, alive = psutil.wait_procs(sparkbot_processes, timeout=3)

    # Force kill if still running
    if alive:
        print("\n   Some processes didn't stop gracefully, force killing...")
        for proc in alive:
            try:
                print(f"   Force killing PID {proc.pid}...")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"   ⚠️  Could not kill PID {proc.pid}: {e}")

    # Final check
    time.sleep(0.5)
    still_running = []
    for proc in sparkbot_processes:
        try:
            if proc.is_running():
                still_running.append(proc.pid)
        except psutil.NoSuchProcess:
            pass

    if still_running:
        print(f"\n❌ Warning: Some processes are still running: {still_running}")
        print("   You may need to kill them manually with Task Manager")
    else:
        print(f"\n✅ Successfully stopped {killed_count} process(es)")

    # Check if port 8000 is still in use
    print("\n🔍 Checking port 8000...")
    port_in_use = False
    for conn in psutil.net_connections():
        if conn.laddr.port == 8000 and conn.status == 'LISTEN':
            port_in_use = True
            try:
                proc = psutil.Process(conn.pid)
                print(f"   ⚠️  Port 8000 is still in use by PID {conn.pid} ({proc.name()})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print(f"   ⚠️  Port 8000 is still in use by PID {conn.pid}")

    if not port_in_use:
        print("   ✅ Port 8000 is free")


if __name__ == "__main__":
    print("=" * 60)
    print("SparkBot Process Manager - STOP")
    print("=" * 60)
    print()

    try:
        stop_sparkbot()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
