# Complete Setup Guide - Fresh Clone/Fork

This guide provides **complete step-by-step instructions** for setting up the Trading Algorithm Document Analyzer from scratch on a new development machine. Perfect for organizational clones and forks.

**Estimated Time:** 15-30 minutes

---

## Table of Contents

1. [Prerequisites & System Requirements](#prerequisites--system-requirements)
2. [Quick Start Checklist](#quick-start-checklist)
3. [Detailed Setup Instructions](#detailed-setup-instructions)
4. [Database Setup & Migrations](#database-setup--migrations)
5. [Verification Steps](#verification-steps)
6. [Common Issues & Solutions](#common-issues--solutions)

---

## Prerequisites & System Requirements

### Required Software

Before starting, ensure you have the following installed:

| Software | Minimum Version | Download/Install |
|----------|----------------|------------------|
| **Git** | 2.x | https://git-scm.com/ |
| **Python** | 3.10+ | https://www.python.org/ (tested with 3.12) |
| **Node.js** | 18+ | https://nodejs.org/ |
| **PostgreSQL** | 15+ | https://www.postgresql.org/ |
| **Poetry** | 1.5+ | https://python-poetry.org/docs/#installation |

### Operating System Support

- ✅ **macOS** (Monterey 12+)
- ✅ **Linux** (Ubuntu 20.04+, Debian 11+)
- ✅ **Windows** (Windows 10/11 with WSL2 recommended)
- ✅ **Docker** (Dev Container support)

### AI Provider API Key

**You need at least ONE of the following:**

| Provider | Get API Key | Format |
|----------|-------------|---------|
| **Anthropic Claude** | https://console.anthropic.com/ | `sk-ant-api03-...` |
| **Google Gemini** | https://makersuite.google.com/app/apikey | `AIzaSy...` |
| **OpenAI** | https://platform.openai.com/api-keys | `sk-...` |

⚠️ **Without an AI API key, the application will not start.**

---

## Quick Start Checklist

Use this checklist to track your progress:

### System Setup
- [ ] Git installed and configured
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] PostgreSQL 15+ installed and running
- [ ] Poetry installed (`curl -sSL https://install.python-poetry.org | python3 -`)

### Repository Setup
- [ ] Repository cloned/forked
- [ ] Python dependencies installed (`poetry install`)
- [ ] Frontend dependencies installed (`cd client && npm install`)

### Database Setup
- [ ] PostgreSQL service running
- [ ] Database created (`docsense`)
- [ ] Event store schema applied
- [ ] Migrations run (sequence column, semantic_ir table)

### Configuration
- [ ] `.env` file created from template
- [ ] At least one AI API key configured
- [ ] DATABASE_URL configured
- [ ] CORS_ORIGINS configured

### Verification
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Health check passes (`/api/v1/health`)
- [ ] All tests pass (`poetry run pytest`)

---

## Detailed Setup Instructions

### Step 1: Install System Dependencies

Choose your operating system:

<details>
<summary><strong>macOS (using Homebrew)</strong></summary>

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.12 node postgresql git

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/Users/$USER/.local/bin:$PATH"

# Start PostgreSQL
brew services start postgresql@15

# Verify installations
python3.12 --version  # Should show Python 3.12.x
node --version        # Should show v18.x or higher
psql --version        # Should show PostgreSQL 15.x
poetry --version      # Should show Poetry 1.5.x or higher
```

</details>

<details>
<summary><strong>Ubuntu/Debian Linux</strong></summary>

```bash
# Update package list
sudo apt update

# Install dependencies
sudo apt install -y \
  python3.12 \
  python3.12-venv \
  python3-pip \
  nodejs \
  npm \
  postgresql \
  postgresql-contrib \
  git

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH (add to ~/.bashrc)
export PATH="/home/$USER/.local/bin:$PATH"
source ~/.bashrc

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installations
python3.12 --version
node --version
psql --version
poetry --version
```

</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
# Install Chocolatey (Windows package manager) if not installed
# Run PowerShell as Administrator:
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install dependencies
choco install python nodejs postgresql git -y

# Install Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Add to PATH (in System Environment Variables)
# Add: C:\Users\<YourUsername>\AppData\Roaming\Python\Scripts

# Start PostgreSQL service
Start-Service postgresql-x64-15

# Verify installations (in new terminal)
python --version
node --version
psql --version
poetry --version
```

**Recommended:** Use WSL2 (Windows Subsystem for Linux) for better compatibility.

</details>

<details>
<summary><strong>Using Dev Container (Recommended for Teams)</strong></summary>

**Prerequisites:**
- Docker Desktop installed
- VS Code with Remote-Containers extension

```bash
# 1. Clone repository
git clone https://github.com/your-org/docsense.git
cd docsense

# 2. Open in VS Code
code .

# 3. When prompted, click "Reopen in Container"
# Everything is pre-configured!

# 4. Once container is running, set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize database (inside container)
psql -U postgres -d docsense -f docs/database/event_store_schema.sql
python scripts/migrate_add_sequence_column.py
python scripts/migrate_create_semantic_ir_table.py

# 6. Start services
# Terminal 1: python main.py
# Terminal 2: cd client && npm run dev
```

The dev container includes:
- ✅ Python 3.12 with Poetry
- ✅ Node.js 18
- ✅ PostgreSQL 15
- ✅ All VS Code extensions
- ✅ Pre-configured environment

</details>

---

### Step 2: Clone/Fork Repository

```bash
# Clone from your organization's repository
git clone https://github.com/your-org/docsense.git
cd docsense

# Or if you forked it
git clone https://github.com/your-username/docsense.git
cd docsense

# Verify you're in the right directory
ls -la
# Should see: client/, docs/, src/, tests/, main.py, pyproject.toml, etc.
```

---

### Step 3: Set Up Python Environment

```bash
# Verify Python version (must be 3.10+)
python3.12 --version

# Install Python dependencies using Poetry
poetry install

# This will:
# - Create a virtual environment
# - Install all dependencies from pyproject.toml
# - Install development dependencies

# Verify installation
poetry run python --version
poetry run python -c "import fastapi; print('FastAPI installed successfully')"

# Expected: "FastAPI installed successfully"
```

**Troubleshooting:**
- If `poetry install` fails, try: `poetry install --no-cache`
- If you get SSL errors, try: `poetry config certificates.authority.verify false` (development only!)

---

### Step 4: Set Up Frontend (Node.js)

```bash
# Navigate to client directory
cd client

# Install Node dependencies
npm install

# This installs:
# - React 18
# - Vite (build tool)
# - Shadcn/ui components
# - Tailwind CSS
# - React Query
# - React Router
# - And all other dependencies

# Verify installation
npm list react
# Should show react@18.x.x

# Return to project root
cd ..
```

**Troubleshooting:**
- If `npm install` fails, try: `rm -rf node_modules package-lock.json && npm install`
- If you get permission errors (Linux), avoid using `sudo npm install`

---

## Database Setup & Migrations

### Step 5: Create PostgreSQL Database

```bash
# Option 1: Using createdb command
createdb -U postgres docsense

# Option 2: Using psql
psql -U postgres
# Then run: CREATE DATABASE docsense;
# Exit with: \q

# Verify database created
psql -U postgres -l | grep docsense
# Should show: docsense | postgres | UTF8 | ...
```

**Default PostgreSQL Credentials:**
- Username: `postgres`
- Password: `postgres` (or empty on macOS Homebrew)
- Host: `localhost`
- Port: `5432`

---

### Step 6: Apply Database Schema

The application uses **Event Sourcing with CQRS**, which requires specific database tables.

#### 6.1 Apply Base Event Store Schema

```bash
# Apply the base schema
psql -U postgres -d docsense -f docs/database/event_store_schema.sql

# Verify tables created
psql -U postgres -d docsense -c "\dt"

# Expected tables:
# - events              (event store - source of truth)
# - snapshots           (aggregate snapshots for performance)
# - document_views      (read model for documents)
# - document_contents   (document markdown content)
# - feedback_views      (read model for feedback)
# - policy_repositories (policy definitions)
# - semantic_ir         (semantic intermediate representation)
# - projection_failures (projection error tracking)
```

#### 6.2 Apply Production Migrations

These migrations were added after initial development and MUST be run:

**Migration 1: Add Sequence Column to Events Table**

```bash
# Navigate to project root
cd /path/to/docsense

# Set DATABASE_URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/docsense"

# Run migration
python scripts/migrate_add_sequence_column.py

# Expected output:
# ✓ Added sequence column to events table
# ✓ Created index on sequence
# ✓ Backfilled sequence for existing events
# ✅ Migration completed successfully!
```

**Verification:**
```bash
psql -U postgres -d docsense -c "\d events"
# Should show 'sequence' column with BIGSERIAL type
```

**Migration 2: Create semantic_ir Table**

```bash
# Run migration
python scripts/migrate_create_semantic_ir_table.py

# Expected output:
# ✓ Created semantic_ir table
# ✓ Created index on document_id
# ✓ Created index on ir_type
# ✓ Created index on name
# ✅ Migration completed successfully!
```

**Verification:**
```bash
psql -U postgres -d docsense -c "\d semantic_ir"
# Should show table with columns: id, document_id, ir_type, name, etc.
```

---

### Step 7: Configure Environment Variables

```bash
# Create .env file from template
cp .env.example .env

# Edit .env file
nano .env  # or vim .env, or code .env
```

**Minimum Required Configuration:**

```bash
# Database (REQUIRED)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docsense

# AI Provider (REQUIRED - choose at least ONE)
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
# OR
GEMINI_API_KEY=AIzaSyYOUR_KEY_HERE
# OR
OPENAI_API_KEY=sk-YOUR_KEY_HERE

# CORS (REQUIRED)
CORS_ORIGINS=http://localhost:5000

# Application Settings (OPTIONAL - these are defaults)
ENVIRONMENT=development
LOG_LEVEL=INFO
LOG_FORMAT=text
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
```

**Full Development Configuration (Recommended):**

```bash
# ============================================
# DEVELOPMENT ENVIRONMENT CONFIGURATION
# ============================================

# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docsense
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20

# AI Providers (configure all for testing different models)
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
GEMINI_API_KEY=AIzaSyYOUR_KEY_HERE
OPENAI_API_KEY=sk-YOUR_KEY_HERE
DEFAULT_AI_PROVIDER=gemini

# CORS (frontend URL)
CORS_ORIGINS=http://localhost:5000,http://localhost:3000

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Development Features
DEBUG=true
ENABLE_DOCS=true
HOT_RELOAD=true
SAVE_AI_RESPONSES=true

# Authentication (development bypass)
DEV_AUTH_BYPASS=true
DEV_TEST_USER_KERBEROS=testuser
DEV_TEST_USER_GROUPS=developers,analysts

# Optional: Sentry for error tracking
# SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
```

**Security Notes:**
- ⚠️ **NEVER commit `.env` to version control**
- ✅ `.env` is already in `.gitignore`
- ✅ Use `.env.example` as a template for team members
- ✅ For production, use secrets managers (Doppler, AWS Secrets Manager, etc.)

---

## Verification Steps

### Step 8: Verify Backend Setup

```bash
# Start backend
python main.py

# You should see:
# ✓ Configuration validated successfully
# ✓ Database pool initialized
# ✓ Application started on http://0.0.0.0:8000

# In another terminal, test health check
curl http://localhost:8000/api/v1/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "database": {
      "status": "healthy",
      "message": "Database operational"
    },
    "event_store": {
      "status": "healthy",
      "message": "Event store operational"
    }
  }
}
```

**If backend doesn't start, check:**
1. DATABASE_URL is correct
2. PostgreSQL is running: `pg_isready`
3. At least one AI API key is set
4. Port 8000 is not in use: `lsof -i :8000`

---

### Step 9: Verify Frontend Setup

```bash
# In a new terminal, navigate to client
cd client

# Start frontend dev server
npm run dev

# You should see:
# VITE v5.x.x  ready in XXX ms
# ➜  Local:   http://localhost:5000/
# ➜  Network: use --host to expose

# Test frontend (in another terminal)
curl http://localhost:5000/

# Should return HTML (React app)
```

**If frontend doesn't start, check:**
1. Node modules installed: `ls node_modules/`
2. Port 5000 is not in use: `lsof -i :5000`
3. Backend is running (frontend calls API)

---

### Step 10: Run Test Suite

```bash
# Run all backend tests (373 tests)
poetry run pytest

# Expected output:
# ============================= test session starts ==============================
# collected 373 items
# ...
# ========================= 373 passed in XX.XXs =========================

# Run specific test categories
poetry run pytest tests/unit/domain/        # Domain layer (133 tests)
poetry run pytest tests/unit/infrastructure/ # Infrastructure (55 tests)
poetry run pytest tests/unit/application/   # Application (65 tests)
poetry run pytest tests/unit/infrastructure/ai/ # AI layer (94 tests)
poetry run pytest tests/unit/api/           # API layer (26 tests)

# Run integration tests
poetry run pytest tests/integration/

# Run with coverage report
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report
```

**Frontend Tests:**

```bash
cd client
npm test

# Expected: All tests pass
```

---

### Step 11: Full End-to-End Verification

```bash
# 1. Backend running on port 8000
# Terminal 1:
python main.py

# 2. Frontend running on port 5000
# Terminal 2:
cd client && npm run dev

# 3. Access application
# Open browser: http://localhost:5000

# 4. Test document upload
# - Click "Upload Document"
# - Upload a PDF or Word file
# - Verify conversion succeeds
# - Verify document appears in list

# 5. Test AI analysis
# - Select a document
# - Click "Analyze"
# - Select policy repository
# - Verify analysis completes
# - Review feedback

# 6. Check metrics endpoint
curl http://localhost:8000/metrics
# Should return Prometheus metrics

# 7. Check API documentation
# Open browser: http://localhost:8000/docs
# Should show Swagger UI
```

---

## Common Issues & Solutions

### Issue 1: "Configuration validation failed: DATABASE_URL"

**Symptoms:**
```
Configuration validation failed:
  DATABASE_URL: Field required
```

**Solutions:**
```bash
# 1. Verify .env file exists
ls -la .env

# 2. Check DATABASE_URL is set
cat .env | grep DATABASE_URL

# 3. Ensure no typos (common mistake: DATABSE_URL)
# Correct: DATABASE_URL=postgresql://...

# 4. Test database connection manually
psql "postgresql://postgres:postgres@localhost:5432/docsense" -c "SELECT 1;"
```

---

### Issue 2: "At least one AI provider API key required"

**Symptoms:**
```
Configuration validation failed:
  : At least one AI provider API key must be configured
```

**Solutions:**
```bash
# 1. Check .env file for API keys
cat .env | grep API_KEY

# 2. Ensure no placeholder values
# ❌ WRONG: ANTHROPIC_API_KEY=your-key-here
# ✅ CORRECT: ANTHROPIC_API_KEY=sk-ant-api03-actual-key

# 3. Get API key from provider
# Anthropic: https://console.anthropic.com/
# Gemini: https://makersuite.google.com/app/apikey
# OpenAI: https://platform.openai.com/api-keys

# 4. Add to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

---

### Issue 3: "Database connection refused"

**Symptoms:**
```
asyncpg.exceptions.ConnectionDoesNotExistError
could not connect to server: Connection refused
```

**Solutions:**
```bash
# 1. Check PostgreSQL is running
# macOS:
brew services list | grep postgresql
brew services start postgresql

# Linux:
sudo systemctl status postgresql
sudo systemctl start postgresql

# Windows:
net start postgresql-x64-15

# 2. Verify database exists
psql -U postgres -l | grep docsense

# 3. Test connection
psql -U postgres -d docsense -c "SELECT 1;"

# 4. Check DATABASE_URL format
# Correct format: postgresql://user:password@host:port/database
# Example: postgresql://postgres:postgres@localhost:5432/docsense
```

---

### Issue 4: "ModuleNotFoundError: No module named 'fastapi'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**
```bash
# 1. Verify Poetry environment is activated
poetry env info

# 2. Reinstall dependencies
poetry install

# 3. Clear cache and reinstall (if issue persists)
poetry cache clear pypi --all
poetry install

# 4. Verify installation
poetry run python -c "import fastapi; print(fastapi.__version__)"
```

---

### Issue 5: "Port 8000 already in use"

**Symptoms:**
```
Error: [Errno 48] Address already in use
```

**Solutions:**
```bash
# 1. Find process using port 8000
# macOS/Linux:
lsof -ti:8000

# Windows:
netstat -ano | findstr :8000

# 2. Kill the process
# macOS/Linux:
kill -9 $(lsof -ti:8000)

# Windows:
taskkill /PID <PID> /F

# 3. Or use a different port
PORT=8001 python main.py
```

---

### Issue 6: "npm install fails with permission errors"

**Symptoms:**
```
EACCES: permission denied
```

**Solutions:**
```bash
# 1. NEVER use sudo npm install (creates permission issues)

# 2. Fix npm permissions
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH

# 3. Retry installation
cd client
rm -rf node_modules package-lock.json
npm install

# 4. If still failing, use nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
npm install
```

---

### Issue 7: "Tests fail with database errors"

**Symptoms:**
```
tests fail with "relation does not exist" errors
```

**Solutions:**
```bash
# 1. Ensure migrations were run
python scripts/migrate_add_sequence_column.py
python scripts/migrate_create_semantic_ir_table.py

# 2. Verify schema
psql -U postgres -d docsense -c "\dt"

# 3. Check for missing tables
psql -U postgres -d docsense -f docs/database/event_store_schema.sql

# 4. Run tests with verbose output
poetry run pytest -vv --log-cli-level=DEBUG
```

---

## Additional Resources

### Environment Variable Reference
See [Environment Variables Documentation](docs/deployment/environment-variables.md) for complete reference.

### Architecture Documentation
- [System Overview](docs/architecture/SYSTEM_OVERVIEW.md)
- [Architecture Decisions](docs/decisions/)
- [Glossary](docs/GLOSSARY.md)

### Development Guides
- [Document Analysis Workflow](docs/processes/001-document-analysis-workflow.md)
- [Event Evolution Guide](docs/processes/004-evolving-events.md)
- [Testing Strategy](docs/testing/TEST_COVERAGE_SUMMARY.md)

### Production Deployment
- [Production Deployment Guide](docs/deployment/production-deployment-guide.md)
- [Database Migration Runbook](docs/deployment/database-migration-runbook.md)

---

## Success Checklist

Congratulations! Your development environment is ready when:

- ✅ Backend starts without errors
- ✅ Frontend loads in browser (http://localhost:5000)
- ✅ Health check returns `{"status": "healthy"}`
- ✅ All 373 tests pass
- ✅ Can upload a document
- ✅ Can run AI analysis
- ✅ API documentation loads (http://localhost:8000/docs)
- ✅ Database has expected tables
- ✅ Metrics endpoint returns data (http://localhost:8000/metrics)

---

## Next Steps

Now that your environment is set up:

1. **Read the Vision** - [VISION.md](docs/VISION.md)
2. **Learn the Language** - [GLOSSARY.md](docs/GLOSSARY.md)
3. **Understand Architecture** - [ADRs](docs/decisions/)
4. **Explore Codebase** - Start with `src/domain/aggregates/document.py`
5. **Run through Workflow** - [Document Analysis Workflow](docs/processes/001-document-analysis-workflow.md)
6. **Pick an Issue** - Contribute to the project!

---

## Getting Help

**Issues during setup?**
- Check this troubleshooting guide
- Review [Development Environment Setup](docs/processes/003-development-environment-setup.md)
- Check [Environment Variables](docs/deployment/environment-variables.md)
- Open an issue on GitHub
- Contact your team lead

**General questions?**
- Check [documentation](docs/)
- Review [test files](tests/) for usage examples
- Ask in team chat

---

## Summary: Minimal Quick Start

For experienced developers who just need the commands:

```bash
# 1. Clone
git clone https://github.com/your-org/docsense.git && cd docsense

# 2. Install dependencies
poetry install && cd client && npm install && cd ..

# 3. Database
createdb -U postgres docsense
psql -U postgres -d docsense -f docs/database/event_store_schema.sql
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/docsense"
python scripts/migrate_add_sequence_column.py
python scripts/migrate_create_semantic_ir_table.py

# 4. Configure
cp .env.example .env
# Edit .env: Set DATABASE_URL and at least one AI API key

# 5. Verify
poetry run pytest  # All tests should pass

# 6. Run
python main.py &  # Backend on :8000
cd client && npm run dev  # Frontend on :5000
```

Access: http://localhost:5000

---

**Setup complete!** You're ready to develop. 🚀
