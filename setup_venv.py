#!/usr/bin/env python3
"""Standalone virtual environment setup script for Vela"""

import os
import sys
import subprocess
from pathlib import Path


def find_python_313():
    """Find Python 3.13.x executable"""
    print("🔍 Searching for Python 3.13...")

    # Possible locations for Python 3.13
    possible_paths = [
        '/opt/homebrew/bin/python3.13',  # Homebrew on Apple Silicon
        '/usr/local/bin/python3.13',      # Homebrew on Intel Mac
        '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3',  # python.org installer
        'python3.13',  # In PATH
    ]

    # On Windows, check for py launcher
    if sys.platform == 'win32':
        possible_paths = [
            'py -3.13',  # Python launcher
            'python3.13',
            r'C:\Python313\python.exe',
            r'C:\Program Files\Python313\python.exe',
        ]

    for python_path in possible_paths:
        try:
            # Handle py launcher separately
            if python_path.startswith('py '):
                cmd = python_path.split()
                cmd.append('--version')
            else:
                cmd = [python_path, '--version']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=(sys.platform == 'win32' and 'py ' in python_path)
            )

            if result.returncode == 0 and '3.13' in result.stdout:
                version_output = result.stdout.strip()
                print(f"✅ Found {version_output}")

                # Return the actual python path for py launcher
                if python_path.startswith('py '):
                    # Get the actual python path
                    get_path = subprocess.run(
                        python_path.split() + ['-c', 'import sys; print(sys.executable)'],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    if get_path.returncode == 0:
                        return get_path.stdout.strip()

                return python_path
        except (FileNotFoundError, PermissionError):
            continue

    return None


def create_venv(python_path, venv_dir='.venv'):
    """Create a virtual environment using the specified Python"""
    venv_path = Path(venv_dir)

    if venv_path.exists():
        print(f"⚠️  Virtual environment already exists at {venv_dir}/")
        response = input("Delete and recreate? (y/N): ").strip().lower()

        if response == 'y':
            print(f"🗑️  Removing existing {venv_dir}/...")
            import shutil
            shutil.rmtree(venv_path)
        else:
            print("❌ Cancelled")
            return False

    print(f"🔨 Creating virtual environment at {venv_dir}/...")

    try:
        # Use subprocess to call python -m venv
        cmd = [python_path, '-m', 'venv', venv_dir]
        result = subprocess.run(cmd, check=True)
        print(f"✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False


def install_dependencies(venv_dir='.venv'):
    """Install dependencies from requirements.txt"""
    venv_path = Path(venv_dir)

    # Determine pip path
    if sys.platform == 'win32':
        pip_path = venv_path / 'Scripts' / 'pip.exe'
        python_path = venv_path / 'Scripts' / 'python.exe'
    else:
        pip_path = venv_path / 'bin' / 'pip'
        python_path = venv_path / 'bin' / 'python'

    if not pip_path.exists():
        print(f"❌ pip not found at {pip_path}")
        return False

    print("\n📥 Installing dependencies from requirements.txt...")
    print("(This may take a few minutes...)\n")

    try:
        # Upgrade pip first
        subprocess.run(
            [str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip'],
            check=True
        )

        # Install requirements
        result = subprocess.run(
            [str(pip_path), 'install', '-r', 'requirements.txt'],
            check=True
        )

        print("\n✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to install dependencies: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Failed to install dependencies: {e}")
        return False


def verify_venv(venv_dir='.venv'):
    """Verify the virtual environment and its Python version"""
    venv_path = Path(venv_dir)

    if not venv_path.exists():
        return False, "Virtual environment does not exist"

    # Determine python path
    if sys.platform == 'win32':
        python_path = venv_path / 'Scripts' / 'python.exe'
    else:
        python_path = venv_path / 'bin' / 'python'

    if not python_path.exists():
        return False, "Python executable not found in venv"

    try:
        # Check Python version
        result = subprocess.run(
            [str(python_path), '--version'],
            capture_output=True,
            text=True,
            check=True
        )

        version = result.stdout.strip()

        # Check if it's Python 3.13
        if '3.13' not in version:
            return False, f"Wrong Python version: {version} (expected 3.13.x)"

        return True, version
    except Exception as e:
        return False, f"Failed to verify: {e}"


def main():
    print("""
╔═══════════════════════════════════════╗
║     Vela Virtual Environment Setup    ║
╚═══════════════════════════════════════╝
    """)

    # Check if we're in the right directory
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt not found!")
        print("Please run this script from the Vela project root directory.")
        sys.exit(1)

    # Find Python 3.13
    python313 = find_python_313()

    if not python313:
        print("\n❌ Python 3.13 not found!")
        print("\nPlease install Python 3.13 first:")
        print("  macOS:   brew install python@3.13")
        print("  Windows: Download from https://www.python.org/downloads/")
        print("  Linux:   Use your package manager or pyenv")
        sys.exit(1)

    print(f"Using: {python313}\n")

    # Create venv
    if not create_venv(python313):
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Verify setup
    print("\n🔍 Verifying setup...")
    success, message = verify_venv()

    if success:
        print(f"✅ {message}")
        print("\n" + "="*50)
        print("✅ Setup complete!")
        print("="*50)
        print("\nYou can now run:")
        print("  python start.py")
    else:
        print(f"❌ Verification failed: {message}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
