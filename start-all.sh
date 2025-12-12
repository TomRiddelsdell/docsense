#!/bin/bash
# DocSense - Start All Services
# This script starts all required services for local development

echo "🚀 Starting DocSense Services..."
echo ""

# Start PostgreSQL database if not already running
echo "📦 Checking PostgreSQL..."
if ! docker ps | grep -q docsense-postgres; then
    echo "Starting PostgreSQL container..."
    docker-compose up -d
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
else
    echo "✓ PostgreSQL already running"
fi

echo ""
echo "🌐 Starting Backend API on port 8000..."
echo "   (Running in background with DATABASE_URL)"
echo ""

# Start backend in the background
DATABASE_URL="postgresql://docsense:docsense_local_dev@localhost:5432/docsense" \
    poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo ""
echo "⚛️  Starting Frontend on port 5000..."
echo "   (Navigate to client directory and run npm run dev)"
echo ""

echo "✅ Services Started!"
echo ""
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Frontend:     http://localhost:5000 (after running 'npm run dev' in /client)"
echo ""
echo "   Backend PID: $BACKEND_PID"
echo ""
echo "To view backend logs: tail -f /tmp/backend.log"
echo "To stop backend: kill $BACKEND_PID"
echo ""
echo "For frontend, run in separate terminal:"
echo "   cd client && npm run dev"
