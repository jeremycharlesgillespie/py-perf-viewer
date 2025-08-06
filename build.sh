#!/bin/bash
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
