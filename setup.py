#!/usr/bin/env python3
"""
Setup script for py-perf-viewer with Vue.js SPA support.
This script handles both Django backend and Vue.js frontend setup.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"🔧 Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def check_command_exists(command):
    """Check if a command exists in the system."""
    return shutil.which(command) is not None

def setup_python_environment():
    """Set up Python virtual environment and Django dependencies."""
    print("🐍 Setting up Python environment...")
    
    # Check if virtual environment exists
    if not os.path.exists('.venv'):
        print("📦 Creating Python virtual environment...")
        run_command("python3 -m venv .venv")
    else:
        print("✅ Virtual environment already exists")
    
    # Install Python dependencies
    print("📦 Installing Python dependencies...")
    run_command(".venv/bin/pip install --upgrade pip")
    run_command(".venv/bin/pip install -r requirements.txt")
    
    # Install development dependencies if available
    if os.path.exists("requirements-dev.txt"):
        run_command(".venv/bin/pip install -r requirements-dev.txt")

def setup_django():
    """Set up Django application."""
    print("🌐 Setting up Django...")
    
    # Run migrations
    print("🗄️  Running Django migrations...")
    run_command(".venv/bin/python manage.py migrate")
    
    # Collect static files
    print("📁 Collecting static files...")
    run_command(".venv/bin/python manage.py collectstatic --noinput")

def setup_nodejs():
    """Set up Node.js environment and Vue.js dependencies."""
    print("📦 Setting up Node.js environment...")
    
    # Check if Node.js is installed
    if not check_command_exists("node"):
        print("❌ Node.js is not installed!")
        print("💡 Please install Node.js from https://nodejs.org/ or using:")
        print("   macOS: brew install node")
        print("   Ubuntu/Debian: sudo apt install nodejs npm")
        print("   Windows: Download from https://nodejs.org/")
        sys.exit(1)
    
    # Check Node.js version
    result = run_command("node --version", check=False)
    if result:
        node_version = result.stdout.strip()
        print(f"✅ Node.js version: {node_version}")
    
    # Check if npm is available
    if not check_command_exists("npm"):
        print("❌ npm is not installed!")
        sys.exit(1)
    
    # Install Node.js dependencies
    if os.path.exists("package.json"):
        print("📦 Installing Node.js dependencies...")
        run_command("npm install")
    else:
        print("❌ package.json not found!")
        sys.exit(1)

def create_env_file():
    """Create .env file for development configuration."""
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file...")
        env_content = """# Development environment configuration
DEBUG=True
DJANGO_SECRET_KEY=your-secret-key-here
VITE_DEV_SERVER=http://localhost:5173
"""
        env_file.write_text(env_content)
        print("✅ Created .env file")
    else:
        print("✅ .env file already exists")

def create_gitignore():
    """Create/update .gitignore file."""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
media/
staticfiles/

# Virtual Environment
.venv/
venv/
ENV/
env/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn-integrity

# Vue.js / Vite
dist/
.vite/
.cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    print("✅ Created/updated .gitignore file")

def setup_development_scripts():
    """Create development helper scripts."""
    print("📝 Creating development scripts...")
    
    # Create start-dev.sh script
    start_dev_content = """#!/bin/bash
# Development startup script for py-perf-viewer Vue.js SPA

echo "🚀 Starting py-perf-viewer development servers..."

# Function to kill background processes on exit
cleanup() {
    echo "🛑 Stopping development servers..."
    jobs -p | xargs -r kill
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Django development server in background
echo "🐍 Starting Django server on http://localhost:8000..."
.venv/bin/python manage.py runserver 8000 &
DJANGO_PID=$!

# Wait a moment for Django to start
sleep 2

# Start Vite development server in background
echo "⚡ Starting Vite dev server on http://localhost:5173..."
npm run dev &
VITE_PID=$!

# Wait a moment for Vite to start
sleep 3

echo ""
echo "✅ Development servers started!"
echo "🌐 Django API server: http://localhost:8000/api/"
echo "⚡ Vite dev server: http://localhost:5173"
echo "🎯 Open your browser to: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for both processes
wait $DJANGO_PID $VITE_PID
"""
    
    with open("start-dev.sh", "w") as f:
        f.write(start_dev_content)
    run_command("chmod +x start-dev.sh")
    
    # Create build.sh script for production
    build_content = """#!/bin/bash
# Production build script for py-perf-viewer Vue.js SPA

echo "🏗️  Building py-perf-viewer for production..."

# Build Vue.js application
echo "📦 Building Vue.js SPA..."
npm run build

# Collect Django static files
echo "📁 Collecting Django static files..."
.venv/bin/python manage.py collectstatic --noinput

echo "✅ Production build complete!"
echo "🚀 You can now deploy the application"
"""
    
    with open("build.sh", "w") as f:
        f.write(build_content)
    run_command("chmod +x build.sh")
    
    print("✅ Created development scripts:")
    print("   - start-dev.sh: Start both Django and Vite dev servers")
    print("   - build.sh: Build for production")

def main():
    """Main setup function."""
    print("🚀 py-perf-viewer Setup Script")
    print("===============================")
    print("Setting up Django backend + Vue.js SPA frontend")
    print()
    
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print(f"📁 Working directory: {script_dir}")
    print()
    
    try:
        # Setup steps
        setup_python_environment()
        print()
        
        setup_django()
        print()
        
        setup_nodejs()
        print()
        
        create_env_file()
        create_gitignore()
        setup_development_scripts()
        print()
        
        print("🎉 Setup Complete!")
        print("==================")
        print()
        print("Next steps:")
        print("1. 🚀 Start development servers:")
        print("   ./start-dev.sh")
        print()
        print("2. 🌐 Open your browser:")
        print("   http://localhost:8000")
        print()
        print("3. 🏗️  For production build:")
        print("   ./build.sh")
        print()
        print("📚 Documentation:")
        print("   - Vue.js app source: ./src/")
        print("   - Django settings: ./pyperfweb/settings.py")
        print("   - API endpoints: http://localhost:8000/api/")
        print()
        
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()