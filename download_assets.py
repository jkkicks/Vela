#!/usr/bin/env python3
"""Download required static assets for the web interface"""
import os
import urllib.request
from pathlib import Path

# Create static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Assets to download
assets = {
    "htmx.min.js": "https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js",
    "alpine.min.js": "https://unpkg.com/alpinejs@3.13.3/dist/cdn.min.js",
}

print("Downloading static assets...")

for filename, url in assets.items():
    filepath = static_dir / filename

    if filepath.exists():
        print(f"[OK] {filename} already exists")
        continue

    try:
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, filepath)
        print(f"[OK] Downloaded {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to download {filename}: {e}")

# Create placeholder CSS file
css_file = static_dir / "custom.css"
if not css_file.exists():
    css_file.write_text("""/* Custom styles for SparkBot */
.htmx-indicator {
    display: none;
}
.htmx-request .htmx-indicator {
    display: inline;
}
.htmx-request.htmx-indicator {
    display: inline;
}
""")
    print("[OK] Created custom.css")

print("\nAll assets downloaded successfully!")