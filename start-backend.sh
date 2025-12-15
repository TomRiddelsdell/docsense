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

# Check if Doppler is available
if command -v doppler &> /dev/null && [ -n "$DOPPLER_TOKEN" ]; then
    echo "🔐 Using Doppler for secrets management"
    echo "🌐 Starting backend API server on port 8000..."
    doppler run -- poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
else
    echo "⚠️  Doppler not available, using .env file"
    if [ ! -f .env ]; then
        echo "❌ No .env file found. Either configure Doppler or create .env from .env.example"
        exit 1
    fi
    echo "🌐 Starting backend API server on port 8000..."
    poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
fi
