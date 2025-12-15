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
if command -v doppler &> /dev/null && [ -n "$DOPPLER_TOKEN" ]; then
    echo "   (Using Doppler for secrets)"
else
    echo "   (Using .env file)"
fi
echo ""

# Start backend in the background
if command -v doppler &> /dev/null && [ -n "$DOPPLER_TOKEN" ]; then
    doppler run -- poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
else
    poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
fi
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo ""
echo "⚛️  Starting Frontend on port 5000..."
echo ""

# Start frontend in the background
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

echo ""
echo "✅ All Services Started!"
echo ""
echo "   Frontend:     http://localhost:5000"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo ""
echo "   Backend PID:  $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   docker-compose down"
echo ""
echo "Logs are available in the terminal output above."
