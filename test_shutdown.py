#!/usr/bin/env python3
"""Test script to verify proper shutdown handling"""

import subprocess
import time
import sys
import signal
import socket

def test_port(port=8000):
    """Check if a port is in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def test_shutdown():
    """Test the shutdown mechanism"""
    print("=== Vela Shutdown Test ===\n")

    # Check if port is already in use
    if test_port():
        print("WARNING: Port 8000 is already in use!")
        print("Killing existing Python processes...")
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'],
                         capture_output=True, check=False)
            subprocess.run(['taskkill', '/F', '/IM', 'python3.exe'],
                         capture_output=True, check=False)
        time.sleep(2)

    # Start Vela
    print("\n1. Starting Vela...")
    if sys.platform == 'win32':
        process = subprocess.Popen(
            [sys.executable, 'start.py'],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        process = subprocess.Popen([sys.executable, 'start.py'])

    # Wait for it to start
    print("   Waiting 8 seconds for startup...")
    time.sleep(8)

    # Check if running
    if test_port():
        print("   [OK] Vela is running (port 8000 is open)")
    else:
        print("   [FAILED] Vela failed to start (port 8000 is not open)")
        process.terminate()
        return

    # Send Ctrl+C
    print("\n2. Sending Ctrl+C signal...")
    if sys.platform == 'win32':
        # On Windows, send CTRL_C_EVENT
        process.send_signal(signal.CTRL_C_EVENT)
    else:
        process.send_signal(signal.SIGINT)

    # Wait for shutdown
    print("   Waiting 5 seconds for shutdown...")
    for i in range(5):
        time.sleep(1)
        if process.poll() is not None:
            print(f"   Process terminated after {i+1} seconds")
            break

    # Check if process terminated
    if process.poll() is None:
        print("   WARNING: Process still running, forcing termination...")
        process.terminate()
        time.sleep(1)
        if process.poll() is None:
            process.kill()

    # Wait a bit more
    time.sleep(2)

    # Test port availability
    print("\n3. Testing port 8000...")
    if test_port():
        print("   [FAILED] Port 8000 is still in use!")
        print("   Running cleanup...")
        if sys.platform == 'win32':
            subprocess.run(['netstat', '-ano', '|', 'findstr', ':8000'],
                         shell=True, capture_output=False)
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe'],
                         capture_output=True, check=False)
    else:
        print("   [SUCCESS] Port 8000 is free!")

    print("\n=== Test Complete ===")

    # Final test: Try to start again
    print("\n4. Testing restart...")
    if sys.platform == 'win32':
        process2 = subprocess.Popen(
            [sys.executable, 'start.py'],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        process2 = subprocess.Popen([sys.executable, 'start.py'])

    print("   Waiting 8 seconds for restart...")
    time.sleep(8)

    if test_port():
        print("   [SUCCESS] Restart successful!")
        # Clean up
        print("\n   Cleaning up test...")
        if sys.platform == 'win32':
            process2.send_signal(signal.CTRL_C_EVENT)
        else:
            process2.send_signal(signal.SIGINT)
        time.sleep(3)
        if process2.poll() is None:
            process2.terminate()
    else:
        print("   [FAILED] Restart failed - port not available")

if __name__ == "__main__":
    test_shutdown()