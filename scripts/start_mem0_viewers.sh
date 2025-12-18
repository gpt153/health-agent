#!/bin/bash
# Start Mem0 viewers (web interface + pgAdmin)

set -e

echo "=============================================="
echo "🧠 Mem0 Memory Viewers Setup"
echo "=============================================="
echo ""

# Check if running in project root
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run from project root directory"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    pip install flask -q
fi

# Start pgAdmin if not running
if ! docker ps | grep -q health-agent-pgadmin; then
    echo "🚀 Starting pgAdmin..."
    docker run -d \
        --name health-agent-pgadmin \
        -p 5050:80 \
        -e PGADMIN_DEFAULT_EMAIL=admin@admin.com \
        -e PGADMIN_DEFAULT_PASSWORD=admin \
        -e PGADMIN_CONFIG_SERVER_MODE=False \
        dpage/pgadmin4 > /dev/null 2>&1

    echo "   Waiting for pgAdmin to start..."
    sleep 8
else
    echo "✅ pgAdmin already running"
fi

# Start web viewer if not running
if ! pgrep -f "mem0_web_viewer.py" > /dev/null; then
    echo "🚀 Starting Web Viewer..."
    nohup python scripts/mem0_web_viewer.py > logs/mem0_viewer.log 2>&1 &
    sleep 3
else
    echo "✅ Web viewer already running"
fi

echo ""
echo "=============================================="
echo "✨ Mem0 Viewers Ready!"
echo "=============================================="
echo ""
echo "📊 WEB VIEWER:"
echo "   URL: http://localhost:5555"
echo "   Features: Browse memories, semantic search"
echo "   Simple, fast, ready to use!"
echo ""
echo "🗄️  PGADMIN (Professional SQL tool):"
echo "   URL: http://localhost:5050"
echo "   Login: admin@admin.com / admin"
echo ""
echo "   Connection details:"
echo "   - Host: host.docker.internal (or your machine IP)"
echo "   - Port: 5434"
echo "   - Database: health_agent"
echo "   - User: postgres"
echo "   - Password: postgres"
echo ""
echo "📝 QUICK COMMANDS:"
echo "   View logs: tail -f logs/mem0_viewer.log"
echo "   Stop all: docker stop health-agent-pgadmin"
echo "   Restart: bash scripts/start_mem0_viewers.sh"
echo ""
echo "=============================================="
