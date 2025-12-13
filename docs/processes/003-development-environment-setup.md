# Process: Development Environment Setup

## Purpose

This process describes how to set up a complete development environment for the Trading Algorithm Document Analyzer. Follow these steps to get a working local development environment.

## Prerequisites

- Git installed
- Docker and Docker Compose installed (for containerized development)
- OR: Python 3.12+, Node.js 18+, PostgreSQL 15+ (for local development)
- Text editor or IDE (VS Code recommended)

## Quick Start (Dev Container - Recommended)

The fastest way to get started is using the provided dev container configuration.

### Step 1: Clone Repository

```bash
git clone https://github.com/TomRiddelsdell/docsense.git
cd docsense
```

### Step 2: Open in VS Code Dev Container

```bash
# Open in VS Code
code .

# VS Code will detect .devcontainer/ and prompt:
# "Reopen in Container"
# Click "Reopen in Container"
```

The dev container includes:
- Python 3.12 with all dependencies
- Node.js 18 with npm
- PostgreSQL 15
- AWS CLI, Docker CLI, Terraform CLI
- Pre-configured VS Code extensions

### Step 3: Initialize Database

```bash
# Inside dev container terminal
psql -U postgres -d docsense -f docs/database/event_store_schema.sql
psql -U postgres -d docsense -f docs/database/projection_failure_tracking.sql
```

### Step 4: Set Up Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Minimum required**:
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docsense
ANTHROPIC_API_KEY=sk-ant-your-key-here  # Or OPENAI_API_KEY or GEMINI_API_KEY
CORS_ORIGINS=http://localhost:5000
```

### Step 5: Start Services

```bash
# Terminal 1: Start backend
python main.py

# Terminal 2: Start frontend
cd client
npm install
npm run dev
```

**Access**:
- Frontend: http://localhost:5000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Manual Setup (Without Dev Container)

If you prefer not to use containers, follow these steps for manual setup.

### Step 1: Install System Dependencies

**macOS**:
```bash
brew install python@3.12 node postgresql git
brew services start postgresql
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install python3.12 python3-pip nodejs npm postgresql git
sudo systemctl start postgresql
```

**Windows**:
- Install Python 3.12 from python.org
- Install Node.js 18+ from nodejs.org
- Install PostgreSQL 15+ from postgresql.org
- Install Git from git-scm.com

### Step 2: Clone and Set Up Python Environment

```bash
# Clone repository
git clone https://github.com/TomRiddelsdell/docsense.git
cd docsense

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install poetry
poetry install
```

### Step 3: Set Up Database

```bash
# Create database
createdb -U postgres docsense

# Initialize schema
psql -U postgres -d docsense -f docs/database/event_store_schema.sql
psql -U postgres -d docsense -f docs/database/projection_failure_tracking.sql

# Verify schema
psql -U postgres -d docsense -c "\dt"
```

### Step 4: Set Up Frontend

```bash
cd client
npm install
cd ..
```

### Step 5: Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit with your values
nano .env
```

**Development .env**:
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docsense
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20

# AI Providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-your-key-here
# OPENAI_API_KEY=sk-your-key-here
# GEMINI_API_KEY=AIza-your-key-here

# CORS
CORS_ORIGINS=http://localhost:5000

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Application
ENVIRONMENT=development
```

### Step 6: Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Frontend tests
cd client
npm test
```

### Step 7: Start Development Servers

```bash
# Terminal 1: Backend (with auto-reload)
poetry run uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Frontend (with hot reload)
cd client
npm run dev
```

---

## Docker Compose Setup

For a complete containerized environment without dev container.

### Step 1: Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### Step 2: Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Initialize database (first time only)
docker-compose exec backend python -c "
import asyncio
from src.infrastructure.persistence.event_store import PostgresEventStore
asyncio.run(PostgresEventStore.initialize_schema())
"
```

### Step 3: Access Services

- Frontend: http://localhost:5000
- Backend: http://localhost:8000
- Database: localhost:5432

### Step 4: Development Workflow

```bash
# Restart backend after code changes
docker-compose restart backend

# Rebuild after dependency changes
docker-compose build backend
docker-compose up -d backend

# View logs
docker-compose logs -f backend

# Run tests in container
docker-compose exec backend pytest

# Access database
docker-compose exec db psql -U postgres -d docsense
```

---

## Verify Installation

Run these commands to verify your setup is working:

```bash
# 1. Backend health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "database": "connected"}

# 2. Frontend loads
curl http://localhost:5000/
# Expected: HTML response

# 3. Run test suite
poetry run pytest -v
# Expected: All tests pass

# 4. Check database connection
psql -U postgres -d docsense -c "SELECT COUNT(*) FROM events;"
# Expected: Query returns successfully

# 5. Verify AI provider configured
curl http://localhost:8000/health/ai
# Expected: {"providers": [{"name": "claude", "status": "available"}]}
```

---

## Development Workflow

### Running Backend

```bash
# Development mode with auto-reload
poetry run uvicorn src.api.main:app --reload --port 8000

# Production mode
python main.py

# Run specific module
poetry run python -m src.api.main
```

### Running Frontend

```bash
cd client

# Development server (hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

### Running Tests

```bash
# All tests
poetry run pytest

# Specific test file
poetry run pytest tests/unit/domain/test_document.py

# With coverage
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html

# Only unit tests
poetry run pytest tests/unit/

# Only integration tests
poetry run pytest tests/integration/

# Verbose output
poetry run pytest -vv

# Stop on first failure
poetry run pytest -x
```

### Code Quality Tools

```bash
# Type checking
poetry run pyright

# Linting
poetry run ruff check src/

# Auto-fix linting issues
poetry run ruff check --fix src/

# Format code
poetry run black src/

# Sort imports
poetry run isort src/
```

---

## Common Issues

### Issue: Database connection refused

```
Error: could not connect to server: Connection refused
```

**Solution**:
```bash
# Check PostgreSQL is running
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Linux
docker-compose ps db                  # Docker

# Start PostgreSQL
brew services start postgresql         # macOS
sudo systemctl start postgresql        # Linux
docker-compose up -d db               # Docker
```

### Issue: Missing Python dependencies

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution**:
```bash
# Reinstall dependencies
poetry install

# Or with pip
pip install -r requirements.txt
```

### Issue: Frontend won't start

```
Error: Cannot find module 'vite'
```

**Solution**:
```bash
cd client
rm -rf node_modules package-lock.json
npm install
```

### Issue: Port already in use

```
Error: Address already in use (port 8000)
```

**Solution**:
```bash
# Find process using port
lsof -ti:8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 $(lsof -ti:8000)  # macOS/Linux

# Or use different port
uvicorn src.api.main:app --port 8001
```

### Issue: AI provider not configured

```
Error: At least one AI provider API key must be configured
```

**Solution**:
```bash
# Verify .env file exists
cat .env | grep API_KEY

# Set API key
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env

# Restart backend
```

---

## IDE Configuration

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense
- ESLint
- Prettier

**.vscode/settings.json**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.pycodestyleEnabled": false,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

### PyCharm

1. Open project in PyCharm
2. Configure interpreter: Settings → Project → Python Interpreter
3. Select Poetry environment
4. Enable pytest: Settings → Tools → Python Integrated Tools → Default test runner: pytest

---

## Next Steps

- Read [VISION.md](../VISION.md) to understand project goals
- Review [GLOSSARY.md](../GLOSSARY.md) for domain terminology
- Check [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) for development roadmap
- Review [ADRs in docs/decisions/](../decisions/) for architecture decisions
- Follow [Document Analysis Workflow](001-document-analysis-workflow.md) to understand the system

---

## Getting Help

- Check documentation in `docs/`
- Review test files in `tests/` for usage examples
- Open an issue on GitHub
- Contact the development team
