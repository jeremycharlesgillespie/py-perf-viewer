#!/usr/bin/env python3
"""
Startup script for py-perf-viewer Django dashboard with Vue.js SPA support.
Handles setup and launches the development server.
"""

import os
import sys
import subprocess
import shutil
import time
import signal
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and handle errors."""
    print(f"🔹 {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def check_nodejs():
    """Check if Node.js and npm are available."""
    if not shutil.which("node"):
        return False, "Node.js not found"
    if not shutil.which("npm"):
        return False, "npm not found"
    
    try:
        result = subprocess.run("node --version", shell=True, capture_output=True, text=True)
        node_version = result.stdout.strip()
        return True, f"Node.js {node_version}"
    except:
        return False, "Unable to check Node.js version"


def setup_vue_development():
    """Set up Vue.js development environment."""
    print("\n⚡ Setting up Vue.js development environment...")
    
    # Check if package.json exists
    if not Path("package.json").exists():
        print("❌ package.json not found. Vue.js SPA not available.")
        return False
    
    # Check Node.js
    nodejs_ok, nodejs_msg = check_nodejs()
    if not nodejs_ok:
        print(f"❌ {nodejs_msg}")
        print("💡 Please install Node.js from https://nodejs.org/")
        print("   macOS: brew install node")
        print("   Ubuntu: sudo apt install nodejs npm")
        return False
    
    print(f"✅ {nodejs_msg}")
    
    # Install npm dependencies
    if not Path("node_modules").exists():
        print("📦 Installing Node.js dependencies...")
        if not run_command("npm install", "Installing Vue.js dependencies"):
            print("❌ Failed to install Node.js dependencies")
            return False
    else:
        print("✅ Node.js dependencies already installed")
    
    return True


def start_development_servers():
    """Start both Django and Vite development servers."""
    print("\n🚀 Starting development servers...")
    
    # List to keep track of child processes
    processes = []
    
    def cleanup_processes(signum=None, frame=None):
        """Clean up child processes on exit."""
        print("\n🛑 Stopping development servers...")
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup_processes)
    signal.signal(signal.SIGTERM, cleanup_processes)
    
    try:
        # Start Django development server
        print("🐍 Starting Django server on port 8000...")
        django_process = subprocess.Popen(
            ["python", "manage.py", "runserver", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(django_process)
        
        # Give Django time to start
        time.sleep(2)
        
        # Check if Vue.js setup is available
        if Path("package.json").exists() and setup_vue_development():
            print("⚡ Starting Vite development server on port 5173...")
            vite_process = subprocess.Popen(
                ["npm", "run", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                universal_newlines=True
            )
            processes.append(vite_process)
            
            # Give Vite time to start
            time.sleep(3)
            
            print("\n✅ Development servers started!")
            print("🌐 Django API server: http://localhost:8000/api/")
            print("⚡ Vite dev server: http://localhost:5173")
            print("🎯 Vue.js SPA: http://localhost:8000")
            print("\n💡 The Vue.js Single Page Application provides:")
            print("   • Zero white flash navigation")
            print("   • Real-time system metrics")
            print("   • Smooth page transitions")
            print("   • Dark mode support")
        else:
            print("\n✅ Django server started!")
            print("🌐 Traditional Django app: http://localhost:8000")
            print("\n💡 For Vue.js SPA features, run: python setup.py")
        
        print("\nPress Ctrl+C to stop all servers")
        
        # Wait for processes to complete
        try:
            while True:
                time.sleep(1)
                # Check if any process has died
                for proc in processes:
                    if proc.poll() is not None:
                        print(f"⚠️  Process {proc.pid} has stopped")
                        cleanup_processes()
        except KeyboardInterrupt:
            cleanup_processes()
            
    except Exception as e:
        print(f"❌ Error starting servers: {e}")
        cleanup_processes()


def main():
    """Main startup process."""
    print("🚀 PyPerf Viewer Dashboard")
    print("=" * 50)
    print("Django backend + Vue.js SPA frontend")
    print()
    
    # Check if we're in the right directory
    if not Path("manage.py").exists():
        print("❌ Error: manage.py not found. Run this script from the py-perf-viewer root.")
        sys.exit(1)
    
    # Check for virtual environment
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        print("⚠️  Warning: No virtual environment detected.")
        print("   Consider running: python -m venv venv && source venv/bin/activate")
    
    # Install/check requirements
    print("📦 Checking Python requirements...")
    if not run_command("pip3 install -r requirements.txt", "Installing/checking requirements"):
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
    
    # Check for Vue.js setup
    if Path("package.json").exists():
        nodejs_ok, nodejs_msg = check_nodejs()
        if nodejs_ok:
            print(f"\n⚡ Vue.js SPA detected - {nodejs_msg}")
            start_development_servers()
        else:
            print(f"\n⚠️  Vue.js SPA available but {nodejs_msg}")
            print("   Install Node.js to enable the Vue.js Single Page Application")
            print("   For now, starting traditional Django server...")
            
            print(f"\n🌐 Starting Django development server...")
            print("   Dashboard: http://localhost:8000")
            print("   Press Ctrl+C to stop")
            print()
            
            try:
                os.system("python manage.py runserver 8000")
            except KeyboardInterrupt:
                print("\n👋 Server stopped by user")
    else:
        print(f"\n🌐 Starting traditional Django server...")
        print("   Dashboard: http://localhost:8000")
        print("   💡 Run 'python setup.py' to set up Vue.js SPA")
        print("   Press Ctrl+C to stop")
        print()
        
        try:
            os.system("python manage.py runserver 8000")
        except KeyboardInterrupt:
            print("\n👋 Server stopped by user")


if __name__ == "__main__":
    main()