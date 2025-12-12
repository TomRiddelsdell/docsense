#!/bin/bash
# Trading Algorithm Document Analyzer - Backend Startup Script
#
# This script starts the PostgreSQL database and backend API server
# with the correct environment configuration for local development.

set -e

echo "🚀 Starting DocSense Backend..."

# Start PostgreSQL if not already running
echo "📦 Checking PostgreSQL..."
if ! docker ps | grep -q docsense-postgres; then
    echo "Starting PostgreSQL container..."
    docker-compose up -d
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
else
    echo "✓ PostgreSQL already running"
fi

# Set DATABASE_URL for local development
export DATABASE_URL="postgresql://docsense:docsense_local_dev@localhost:5432/docsense"

# Check if database connection is working
echo "🔌 Testing database connection..."
if poetry run python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))" 2>/dev/null; then
    echo "✓ Database connection successful"
else
    echo "⚠️  Database connection failed, but continuing anyway..."
fi

# Start the backend server
echo "🌐 Starting backend API server on port 8000..."
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
