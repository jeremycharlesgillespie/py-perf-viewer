# PyPerf Viewer - Vue.js SPA Setup Guide

This guide explains how to set up and run the new Vue.js Single Page Application version of py-perf-viewer.

## ✨ What's New

The py-perf-viewer has been converted to a **Vue.js Single Page Application (SPA)** that provides:

- **🚫 Zero White Flash**: Instant navigation between pages
- **⚡ Real-time Updates**: Live system metrics with auto-refresh
- **🌙 Dark Mode**: Preserved with smooth transitions
- **📱 Responsive**: Mobile-friendly interface
- **🔄 Smooth Transitions**: Page changes with fade effects

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the automated setup script
python3 setup.py

# Start development servers
./start-dev.sh
```

### Option 2: Manual Setup

```bash
# 1. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Set up Django
python manage.py migrate
python manage.py collectstatic --noinput

# 3. Install Node.js dependencies
npm install

# 4. Start development servers (in separate terminals)
# Terminal 1: Django API server
python manage.py runserver 8000

# Terminal 2: Vite development server
npm run dev
```

### Option 3: Use Enhanced Start Script

```bash
# The start_viewer.py script now supports Vue.js automatically
python3 start_viewer.py
```

## 📋 Prerequisites

### Required
- **Python 3.8+** with pip
- **Node.js 16+** with npm

### Installation
- **macOS**: `brew install node`
- **Ubuntu/Debian**: `sudo apt install nodejs npm`
- **Windows**: Download from [nodejs.org](https://nodejs.org/)

## 🏗️ Project Structure

```
py-perf-viewer/
├── setup.py                    # 🆕 Automated setup script
├── start_viewer.py             # 🔄 Enhanced start script
├── start-dev.sh               # 🆕 Development server launcher
├── build.sh                   # 🆕 Production build script
├── package.json               # 🆕 Node.js dependencies
├── vite.config.js             # 🆕 Build configuration
├── src/                       # 🆕 Vue.js source code
│   ├── main.js                # App entry point
│   ├── App.vue                # Main component
│   ├── router/                # Vue Router configuration
│   ├── views/                 # Page components
│   │   ├── Dashboard.vue      # Home page
│   │   ├── SystemOverview.vue # System metrics overview
│   │   └── SystemDetail.vue   # System detail view
│   ├── stores/                # State management (Pinia)
│   ├── services/              # API layer
│   └── assets/                # CSS and static files
└── pyperfweb/dashboard/
    ├── templates/spa/         # 🆕 SPA template
    ├── api_urls.py           # 🆕 Separated API URLs
    └── views.py              # Updated with SPA view
```

## 🖥️ Development Workflow

### Starting Development
```bash
# Option 1: Use automated script
./start-dev.sh

# Option 2: Use enhanced start script
python3 start_viewer.py

# Option 3: Manual start
python manage.py runserver 8000 &  # Django API
npm run dev                        # Vite dev server
```

### Development URLs
- **🎯 Vue.js SPA**: http://localhost:8000 (main app)
- **🌐 Django API**: http://localhost:8000/api/ (REST endpoints)
- **⚡ Vite Dev Server**: http://localhost:5173 (hot reloading)

### Building for Production
```bash
# Build Vue.js app and collect Django static files
./build.sh

# Or manually:
npm run build
python manage.py collectstatic --noinput
```

## 🎯 Features Implemented

### ✅ Phase 1: Infrastructure
- Vue 3 + Vue Router + Pinia state management
- Vite build system with hot reloading
- API service layer for Django REST endpoints
- Bootstrap integration with dark mode

### ✅ Phase 2: System Metrics (NO WHITE FLASH!)
- **SystemOverview.vue**: Real-time system metrics table
- **SystemDetail.vue**: Detailed host metrics with charts placeholder
- **Smooth Navigation**: Instant client-side routing
- **Auto-refresh**: Live data updates every 60 seconds

### ⏳ Phase 3: Remaining Views (In Progress)
- Performance Records view
- Record Detail view  
- Function Analysis view
- Timeline Viewer

## 🔧 Configuration

### Django Settings
The Vue.js SPA is served through Django's URL system:
- API endpoints: `/api/*` → Django REST views
- All other routes: `/*` → Vue.js SPA

### Development vs Production
- **Development**: Vite dev server with hot reloading
- **Production**: Built assets served by Django

### Environment Variables
Create `.env` file for custom configuration:
```bash
DEBUG=True
DJANGO_SECRET_KEY=your-secret-key
VITE_DEV_SERVER=http://localhost:5173
```

## 🐛 Troubleshooting

### Node.js Not Found
```bash
# Install Node.js
brew install node          # macOS
sudo apt install nodejs npm # Ubuntu

# Verify installation
node --version
npm --version
```

### Port Conflicts
- Django runs on port 8000
- Vite runs on port 5173
- Change ports in `vite.config.js` or Django settings if needed

### Build Issues
```bash
# Clear caches and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Django static files
rm -rf staticfiles/
python manage.py collectstatic --noinput
```

## 📚 API Documentation

The Vue.js app consumes these Django REST endpoints:

### System Metrics
- `GET /api/system/` - System dashboard data
- `GET /api/system/?hostname=<name>&hours=<hours>` - Host detail
- `GET /api/system/hostnames/` - List of hostnames

### Performance Metrics  
- `GET /api/metrics/` - Performance overview
- `GET /api/hostnames/` - Performance hostnames
- `GET /api/functions/` - Function list
- `GET /api/timeline/` - Timeline data

## 🎉 Benefits of Vue.js SPA

1. **🚫 Zero White Flash**: No more jarring page reloads
2. **⚡ Faster Navigation**: Instant client-side routing  
3. **📊 Real-time Data**: Reactive updates without page refresh
4. **🌙 Smooth Transitions**: Fade effects between pages
5. **📱 Better Mobile**: Responsive, app-like experience
6. **🔄 Auto-refresh**: Live system monitoring
7. **🎨 Modern UI**: Component-based architecture

## 🚀 Next Steps

1. **Install dependencies**: `python3 setup.py`
2. **Start development**: `./start-dev.sh`
3. **Open browser**: http://localhost:8000
4. **Enjoy smooth navigation!** 🎉

The system metrics section now provides a completely smooth, modern web application experience with zero white flash during navigation!