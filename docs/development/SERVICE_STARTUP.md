# DocSense Development - Service Startup Guide

## Quick Start

### Option 1: Manual Startup (Recommended for Development)

**Terminal 1 - Backend:**
```bash
# Start PostgreSQL (if not running)
docker-compose up -d

# Start backend API
DATABASE_URL="postgresql://docsense:docsense_local_dev@localhost:5432/docsense" \
  poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd client
npm run dev
```

### Option 2: Using start-backend.sh Script

```bash
./start-backend.sh
```

Then in a separate terminal:
```bash
cd client && npm run dev
```

## Service Details

### 1. PostgreSQL Database

**Status Check:**
```bash
docker ps | grep docsense-postgres
```

**Start:**
```bash
docker-compose up -d
```

**Stop:**
```bash
docker-compose down
```

**Connection String:**
```
postgresql://docsense:docsense_local_dev@localhost:5432/docsense
```

### 2. Backend API (FastAPI)

**Port:** 8000

**Endpoints:**
- API: `http://localhost:8000/api/v1/*`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

**Start Command:**
```bash
DATABASE_URL="postgresql://docsense:docsense_local_dev@localhost:5432/docsense" \
  poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Features:**
- Auto-reload on code changes
- OpenAPI documentation at `/docs`
- CORS enabled for `localhost:5000`

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string (required)
- `GEMINI_API_KEY`: For AI analysis (optional for basic ops)
- `ANTHROPIC_API_KEY`: For AI analysis (optional)

### 3. Frontend (React + Vite)

**Port:** 5000

**URL:** `http://localhost:5000`

**Start Command:**
```bash
cd client
npm run dev
```

**Configuration:**
- Vite proxy configured to forward `/api/*` to backend at `http://localhost:8000`
- Hot module replacement (HMR) enabled
- Runs on host `0.0.0.0` (accessible from network)

## Troubleshooting

### 500 Errors on API Endpoints

**Issue:** Getting 500 errors when accessing document endpoints

**Common Causes:**
1. Backend not running
2. Database not accessible
3. Missing environment variables
4. Code errors (check backend logs)

**Solution:**
1. Check backend is running: `curl http://localhost:8000/api/v1/documents`
2. Check database: `docker ps | grep postgres`
3. Review backend logs for errors

### Port Already in Use

**Issue:** "Address already in use" error

**Solution:**
```bash
# Find process using the port
lsof -i :8000  # or :5000 for frontend

# Kill the process
kill -9 <PID>
```

### Database Connection Failed

**Issue:** "Connection refused" or "Cannot connect to database"

**Solution:**
```bash
# Check PostgreSQL container status
docker ps -a | grep postgres

# Check logs
docker logs docsense-postgres

# Restart if needed
docker-compose down && docker-compose up -d
```

### Frontend Can't Connect to Backend

**Issue:** Frontend shows network errors or "Failed to fetch"

**Checklist:**
1. Backend running on port 8000? `curl http://localhost:8000/api/v1/documents`
2. CORS configured correctly? Check backend logs for CORS errors
3. Vite proxy working? Check `client/vite.config.ts`

## Service Architecture

```
┌─────────────────┐
│   Frontend      │  Port: 5000
│  (React/Vite)   │  → /api/* proxied to backend
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Backend API   │  Port: 8000
│    (FastAPI)    │  → /api/v1/* routes
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   PostgreSQL    │  Port: 5432
│    (Docker)     │  → Event store & read models
└─────────────────┘
```

## Development Workflow

### Starting Your Day

```bash
# 1. Pull latest changes
git pull

# 2. Update dependencies
poetry install
cd client && npm install && cd ..

# 3. Start services
./start-backend.sh  # Terminal 1
cd client && npm run dev  # Terminal 2
```

### During Development

- **Backend changes**: Auto-reload is enabled, just save files
- **Frontend changes**: Hot module replacement updates instantly
- **Database schema changes**: May need to restart backend

### Ending Your Day

```bash
# Stop frontend: Ctrl+C in Terminal 2
# Stop backend: Ctrl+C in Terminal 1

# Optionally stop database
docker-compose down
```

## Testing Services

### Backend Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### List Documents

```bash
curl http://localhost:8000/api/v1/documents
```

### Frontend Access

Open browser to: `http://localhost:5000`

## Production Deployment

For production deployment, see:
- `/docs/IMPLEMENTATION_PLAN.md`
- Individual service deployment docs in `/docs/deployment/`

## Need Help?

- Check logs in backend terminal for API errors
- Check browser console for frontend errors
- Review `/docs/TROUBLESHOOTING.md` for common issues
- See `/docs/ARCHITECTURE.md` for system overview
