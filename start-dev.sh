#!/bin/bash
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
