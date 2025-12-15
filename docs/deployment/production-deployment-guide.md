# Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Trading Algorithm Document Analyzer to a production environment.

**Prerequisites:**
- PostgreSQL 15+ database
- Python 3.10+
- Doppler CLI (for secrets management)
- At least one AI provider API key (Claude, Gemini, or OpenAI)
- SSL/TLS certificates for HTTPS
- Reverse proxy (nginx, Apache, or cloud load balancer)

**Deployment Timeline:** 2-4 hours (including testing)

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Application Deployment](#application-deployment)
5. [Monitoring Setup](#monitoring-setup)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying to production, ensure:

- [ ] All tests pass (`poetry run pytest`)
- [ ] Type checking passes (`poetry run pyright`)
- [ ] Linting passes (`poetry run ruff check`)
- [ ] Database migrations tested in staging
- [ ] Environment variables documented and secured
- [ ] AI provider API keys valid and have sufficient quota
- [ ] SSL/TLS certificates obtained and valid
- [ ] Backup strategy defined
- [ ] Monitoring and alerting configured
- [ ] Disaster recovery plan documented

---

## Environment Setup

### 1. Server Provisioning

**Recommended Specifications:**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 50 GB SSD | 100+ GB SSD |
| Network | 100 Mbps | 1 Gbps |

**Operating System:** Ubuntu 22.04 LTS or similar

### 2. Install System Dependencies

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.10+
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Install PostgreSQL client
sudo apt-get install -y postgresql-client

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
export PATH="/root/.local/bin:$PATH"
echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc

# Install Doppler CLI (for secrets management)
curl -sLf --retry 3 --tlsv1.2 --proto "=https" \
  'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/doppler-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/doppler-archive-keyring.gpg] \
  https://packages.doppler.com/public/cli/deb/debian any-version main" \
  | sudo tee /etc/apt/sources.list.d/doppler-cli.list

sudo apt-get update && sudo apt-get install -y doppler
```

### 3. Create Application User

```bash
# Create dedicated user for running the application
sudo useradd -m -s /bin/bash docsense

# Switch to application user
sudo su - docsense
```

### 4. Clone Repository

```bash
# Clone from your repository
git clone https://github.com/your-org/docsense.git /home/docsense/app
cd /home/docsense/app

# Checkout production release
git checkout tags/v1.0.0  # or your release tag
```

### 5. Install Application Dependencies

```bash
cd /home/docsense/app

# Install Python dependencies
poetry install --only main --no-dev

# Verify installation
poetry run python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
```

---

## Database Setup

### 1. Create PostgreSQL Database

```sql
-- Connect to PostgreSQL as admin
psql -U postgres

-- Create database and user
CREATE DATABASE docsense_prod;
CREATE USER docsense_prod WITH PASSWORD 'SECURE_PASSWORD_HERE';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE docsense_prod TO docsense_prod;

-- Connect to database
\c docsense_prod

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify
SELECT * FROM pg_extension WHERE extname = 'uuid-ossp';

\q
```

### 2. Apply Database Schema

```bash
cd /home/docsense/app

# Set database URL (temporarily for migration)
export DATABASE_URL="postgresql://docsense_prod:SECURE_PASSWORD@localhost:5432/docsense_prod"

# Apply event store schema
psql $DATABASE_URL -f docs/database/event_store_schema.sql

# Verify schema
psql $DATABASE_URL -c "\dt"
```

**Expected Tables:**
- `events` - Event store
- `snapshots` - Aggregate snapshots
- `document_views` - Document read model
- `document_contents` - Document markdown content
- `feedback_views` - Feedback read model
- `policy_repositories` - Policy repositories
- `semantic_ir` - Semantic intermediate representation

### 3. Run Migrations

```bash
# Run sequence column migration
DATABASE_URL=$DATABASE_URL poetry run python scripts/migrate_add_sequence_column.py

# Run semantic_ir table migration
DATABASE_URL=$DATABASE_URL poetry run python scripts/migrate_create_semantic_ir_table.py

# Verify migrations
psql $DATABASE_URL -c "SELECT COUNT(*) FROM events;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM semantic_ir;"
```

---

## Application Deployment

### 1. Configure Environment Variables

Use Doppler for secrets management:

```bash
# Login to Doppler
doppler login

# Setup project
doppler setup --project docsense --config production

# Set required secrets
doppler secrets set DATABASE_URL="postgresql://docsense_prod:PASSWORD@localhost:5432/docsense_prod"
doppler secrets set SECRET_KEY="$(openssl rand -hex 32)"
doppler secrets set ANTHROPIC_API_KEY="sk-ant-..."
doppler secrets set GEMINI_API_KEY="..."
doppler secrets set OPENAI_API_KEY="sk-..."

# Set environment-specific variables
doppler secrets set ENVIRONMENT="production"
doppler secrets set LOG_LEVEL="INFO"
doppler secrets set LOG_FORMAT="json"
doppler secrets set CORS_ORIGINS="https://your-domain.com"
doppler secrets set DB_POOL_MIN_SIZE="10"
doppler secrets set DB_POOL_MAX_SIZE="50"

# Verify secrets
doppler secrets
```

**See [Environment Variables](environment-variables.md) for complete reference.**

### 2. Create Systemd Service

Create `/etc/systemd/system/docsense.service`:

```ini
[Unit]
Description=Trading Algorithm Document Analyzer API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=docsense
Group=docsense
WorkingDirectory=/home/docsense/app
Environment="PATH=/home/docsense/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/docsense/app"

# Use Doppler to inject secrets
ExecStart=/usr/bin/doppler run -- \
  /home/docsense/.local/share/pypoetry/venv/bin/poetry run \
  uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=0

# Resource limits
LimitNOFILE=65536
MemoryLimit=4G
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=docsense

[Install]
WantedBy=multi-user.target
```

### 3. Start Application

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable docsense

# Start service
sudo systemctl start docsense

# Check status
sudo systemctl status docsense

# View logs
sudo journalctl -u docsense -f
```

### 4. Configure Reverse Proxy (nginx)

Create `/etc/nginx/sites-available/docsense`:

```nginx
upstream docsense_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-domain.com.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/docsense-access.log;
    error_log /var/log/nginx/docsense-error.log warn;

    # Max upload size (for documents)
    client_max_body_size 50M;

    # API endpoints
    location /api/ {
        proxy_pass http://docsense_backend;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;  # 5 minutes for analysis
    }

    # Metrics endpoint (restrict access)
    location /metrics {
        proxy_pass http://docsense_backend;

        # Restrict to monitoring system IP
        allow 10.0.0.0/8;  # Internal network
        deny all;
    }

    # Health check
    location /api/v1/health {
        proxy_pass http://docsense_backend;
        access_log off;
    }

    # Static files (if serving frontend)
    location / {
        root /home/docsense/app/client/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/docsense /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Monitoring Setup

### 1. Prometheus Configuration

Add to `/etc/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'docsense'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboard

Import the provided Grafana dashboard:

```bash
# Dashboard JSON available at:
# docs/monitoring/grafana-dashboard.json
```

**Key Metrics to Monitor:**
- HTTP request rate and duration
- Document upload success/failure rate
- Analysis completion rate
- Event store operations
- Database pool utilization
- Error rates

### 3. Log Aggregation

Configure log shipping to your log aggregation system (ELK, Splunk, CloudWatch):

```bash
# Example: Filebeat configuration for shipping to Elasticsearch
# /etc/filebeat/filebeat.yml

filebeat.inputs:
  - type: journald
    id: docsense
    include_matches:
      - "SYSLOG_IDENTIFIER=docsense"

output.elasticsearch:
  hosts: ["https://elasticsearch:9200"]
  index: "docsense-logs-%{+yyyy.MM.dd}"

processors:
  - decode_json_fields:
      fields: ["message"]
      target: "json"
```

### 4. Alerting Rules

Configure alerts in Prometheus/Grafana:

```yaml
# example-alerts.yml

groups:
  - name: docsense
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: DatabasePoolExhausted
        expr: db_pool_active_connections / db_pool_size > 0.9
        for: 2m
        annotations:
          summary: "Database pool nearly exhausted"

      - alert: SlowRequests
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "95th percentile latency > 5s"
```

---

## Post-Deployment Verification

### 1. Health Check

```bash
# Check application health
curl https://your-domain.com/api/v1/health

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

### 2. Metrics Verification

```bash
# Check metrics endpoint (from allowed IP)
curl http://localhost:8000/metrics

# Should see Prometheus metrics:
# - http_requests_total
# - http_request_duration_seconds
# - documents_uploaded_total
# - etc.
```

### 3. Functional Testing

```bash
# Upload a test document
curl -X POST https://your-domain.com/api/v1/documents \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.pdf"

# Verify document appears in database
psql $DATABASE_URL -c "SELECT id, filename FROM document_views ORDER BY created_at DESC LIMIT 1;"
```

### 4. Log Verification

```bash
# Check structured JSON logs
sudo journalctl -u docsense -n 50 | jq '.'

# Should see:
# - timestamp, level, logger, message
# - correlation_id for each request
# - HTTP request/response logs
# - No ERROR level entries (unless expected)
```

---

## Rollback Procedures

### 1. Application Rollback

```bash
# Stop current version
sudo systemctl stop docsense

# Switch to previous release
cd /home/docsense/app
git checkout tags/v0.9.0  # previous version

# Reinstall dependencies
poetry install --only main

# Restart
sudo systemctl start docsense

# Verify
sudo systemctl status docsense
```

### 2. Database Rollback

**IMPORTANT:** Event sourcing makes database rollback complex. Never delete events.

If a migration needs to be reverted:

```bash
# 1. Stop application
sudo systemctl stop docsense

# 2. Connect to database
psql $DATABASE_URL

# 3. Drop new tables/columns (example)
ALTER TABLE events DROP COLUMN IF EXISTS sequence;
DROP TABLE IF EXISTS semantic_ir;

# 4. Restart application with previous version
sudo systemctl start docsense
```

**Best Practice:** Test migrations thoroughly in staging before production.

---

## Troubleshooting

### Application Won't Start

**Symptoms:** `systemctl status docsense` shows failed status

**Solutions:**
1. Check logs: `sudo journalctl -u docsense -n 100`
2. Verify environment variables: `doppler secrets`
3. Test database connection: `psql $DATABASE_URL -c "SELECT 1;"`
4. Check Python environment: `poetry run python -c "import fastapi"`
5. Verify file permissions: `ls -la /home/docsense/app`

### High Memory Usage

**Symptoms:** Application OOM killed or slow

**Solutions:**
1. Check worker count: Reduce `--workers` in systemd service
2. Adjust pool size: Lower `DB_POOL_MAX_SIZE`
3. Monitor metrics: Check `db_pool_active_connections`
4. Add swap space: `sudo fallocate -l 4G /swapfile`

### Database Connection Issues

**Symptoms:** `asyncpg.exceptions.ConnectionDoesNotExistError`

**Solutions:**
1. Check PostgreSQL status: `sudo systemctl status postgresql`
2. Verify DATABASE_URL: `doppler secrets get DATABASE_URL`
3. Test connection: `psql $DATABASE_URL -c "SELECT version();"`
4. Check pool exhaustion: Monitor `db_pool_utilization_percent`
5. Increase pool size: Adjust `DB_POOL_MAX_SIZE`

### Slow API Responses

**Symptoms:** Request duration > 2 seconds

**Solutions:**
1. Check metrics: Query `http_request_duration_seconds`
2. Monitor event store: Check `event_store_operation_duration_seconds`
3. Review slow queries: Enable PostgreSQL slow query log
4. Optimize projections: Add database indexes
5. Scale horizontally: Add more workers/instances

### Failed Document Uploads

**Symptoms:** `documents_uploaded_total{status="failed"}` increasing

**Solutions:**
1. Check logs: `sudo journalctl -u docsense | grep -i error`
2. Verify file format: Ensure supported format (PDF, DOCX, etc.)
3. Check disk space: `df -h`
4. Monitor memory: `free -h`
5. Review conversion errors: Check `documents_converted_total{status="failed"}`

---

## Security Considerations

### 1. Network Security

- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Database not exposed to internet
- [ ] Metrics endpoint restricted to internal network
- [ ] Rate limiting enabled on API endpoints

### 2. Secrets Management

- [ ] All secrets stored in Doppler (not in environment files)
- [ ] Secret rotation policy defined
- [ ] API keys have minimum required permissions
- [ ] DATABASE_URL never logged or exposed

### 3. Application Security

- [ ] CORS origins restricted to known domains
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Security headers configured (HSTS, X-Frame-Options, etc.)
- [ ] File upload size limits enforced
- [ ] Input validation on all API endpoints

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor error rates and alert dashboards
- Review application logs for anomalies
- Check database disk usage

**Weekly:**
- Review slow query logs
- Analyze performance metrics trends
- Update security patches

**Monthly:**
- Rotate API keys
- Review and optimize database indexes
- Test backup and restore procedures
- Update dependencies (security patches)

---

## Support

**For production issues:**
- Check this guide first
- Review logs: `sudo journalctl -u docsense`
- Check metrics: `http://localhost:8000/metrics`
- Contact: ops@your-domain.com

**For emergencies:**
- On-call: +1-XXX-XXX-XXXX
- Slack: #docsense-ops
