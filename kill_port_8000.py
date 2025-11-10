#!/usr/bin/env python3
"""
Kill any process using port 8000 on Windows
"""

import subprocess
import sys
import re
import time

def find_process_on_port(port):
    """Find the PID of the process using the specified port"""
    try:
        # Run netstat to find the process
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            check=True
        )

        # Look for lines with the port
        pids = set()
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                # Extract PID (last column)
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)

        return list(pids)
    except Exception as e:
        print(f"Error finding process: {e}")
        return []

def kill_process_by_pid(pid):
    """Kill a process by its PID"""
    try:
        # Use taskkill to force kill the process and its children
        result = subprocess.run(
            ['taskkill', '/F', '/T', '/PID', str(pid)],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            return True, f"Killed process {pid}"
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def main():
    port = 8000

    print(f"Looking for processes on port {port}...")

    pids = find_process_on_port(port)

    if not pids:
        print(f"[OK] No processes found on port {port}")
        return 0

    print(f"Found {len(pids)} process(es) on port {port}: {', '.join(pids)}")

    # Kill each process
    for pid in pids:
        success, message = kill_process_by_pid(pid)
        if success:
            print(f"[OK] {message}")
        else:
            print(f"[FAILED] Failed to kill PID {pid}: {message}")

    # Wait a moment for processes to terminate
    time.sleep(1)

    # Verify the port is free
    remaining = find_process_on_port(port)
    if remaining:
        print(f"[WARNING] Some processes still on port {port}")

        # Try to kill any remaining python processes as a fallback
        print("Attempting fallback: killing all Python processes...")
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'],
                      capture_output=True, check=False)
        subprocess.run(['taskkill', '/F', '/IM', 'python3.exe'],
                      capture_output=True, check=False)
        time.sleep(1)

        remaining = find_process_on_port(port)
        if remaining:
            print(f"[FAILED] Port {port} is still in use")
            return 1

    print(f"[OK] Port {port} is now free")
    return 0

if __name__ == "__main__":
    sys.exit(main())