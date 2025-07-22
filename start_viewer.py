#!/usr/bin/env python3
"""
Startup script for py-perf-viewer Django dashboard.
Handles setup and launches the development server.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔹 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def main():
    """Main startup process."""
    print("🚀 Starting PyPerf Viewer Dashboard")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("manage.py").exists():
        print("❌ Error: manage.py not found. Run this script from the py-perf-viewer root.")
        sys.exit(1)
    
    # Check for virtual environment
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        print("⚠️  Warning: No virtual environment detected.")
        print("   Consider running: python -m venv venv && source venv/bin/activate")
    
    # Install/check requirements
    print("\n📦 Checking requirements...")
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        print("❌ Failed to install requirements. Please check your Python environment.")
        sys.exit(1)
    
    # Run Django migrations
    print("\n🔄 Running Django migrations...")
    if not run_command("python manage.py migrate", "Applying database migrations"):
        print("⚠️  Warning: Migrations failed. Continuing anyway...")
    
    # Collect static files
    print("\n📁 Collecting static files...")
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        print("⚠️  Warning: Static file collection failed. Continuing anyway...")
    
    # Check for py-perf configuration
    config_files = [
        Path(".py-perf.yaml"),
        Path("py-perf.yaml"),
        Path.home() / ".py-perf.yaml",
        Path.home() / ".config" / "py-perf" / "config.yaml"
    ]
    
    config_found = any(cf.exists() for cf in config_files)
    if not config_found:
        print("\n⚠️  No py-perf configuration found!")
        print("   Create a .py-perf.yaml file with your configuration.")
        print("   Example:")
        print("   ---")
        print("   py_perf:")
        print("     enabled: true")
        print("   local:")
        print("     enabled: true")
        print("     data_dir: './perf_data'")
        print("   ---")
    
    # Start Django development server
    print(f"\n🌐 Starting Django development server...")
    print("   Dashboard will be available at: http://localhost:8000")
    print("   Press Ctrl+C to stop the server")
    print()
    
    try:
        # Use os.system to allow Ctrl+C to work properly
        os.system("python manage.py runserver 8000")
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")


if __name__ == "__main__":
    main()