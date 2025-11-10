#!/usr/bin/env python3
"""Simple test to verify Ctrl+C handling works"""

import sys
import time

print("Test started. Press Ctrl+C to test...", flush=True)

try:
    for i in range(100):
        print(f"  Working... {i}", flush=True)
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Caught Ctrl+C!", flush=True)
    print("  Cleaning up...", flush=True)
    time.sleep(1)
    print("  Done!", flush=True)
    print("👋 Goodbye!", flush=True)
finally:
    print("✅ Test complete", flush=True)
    sys.exit(0)
