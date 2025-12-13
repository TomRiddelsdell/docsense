# Process: Production Deployment

## Purpose

This process describes how to deploy the Trading Algorithm Document Analyzer to a production environment. Follow these steps to ensure a safe, reliable deployment with proper validation and rollback capabilities.

## Prerequisites

- Kubernetes cluster or Docker Compose environment configured
- Access to production secrets management (Doppler or AWS Secrets Manager)
- Database backup completed
- All CI/CD tests passing
- Production readiness checklist completed

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (unit, integration, E2E)
- [ ] Code review approved by at least 2 reviewers
- [ ] Database migrations tested on staging
- [ ] Dependency security scan completed (no critical vulnerabilities)
- [ ] Performance testing completed (load testing passed)
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured
- [ ] On-call engineer identified

### Environment Variables

Ensure all required environment variables are set. See [environment-variables.md](../deployment/environment-variables.md) for complete reference.

**Critical Variables**:
```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# AI Providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# CORS Security
CORS_ORIGINS=https://app.example.com,https://www.example.com

# Database Pool
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=50

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Application
ENVIRONMENT=production
```

**Validation**:
```bash
# The application validates configuration at startup
# If validation fails, check logs for specific errors:
docker logs <container-id> | grep "Configuration validation failed"
```

### Step 1: Database Migration

Apply database migrations before deploying new code.

```bash
# 1. Create database backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Apply event store schema (if first deployment)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f docs/database/event_store_schema.sql

# 3. Apply projection failure tracking (if not already applied)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f docs/database/projection_failure_tracking.sql

# 4. Verify schema version
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;"
```

**Rollback**: Restore from backup if migration fails:
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup_YYYYMMDD_HHMMSS.sql
```

### Step 2: Build and Push Images

Build production Docker images and push to container registry.

```bash
# 1. Build backend image
docker build -t docsense-backend:${VERSION} -f Dockerfile .
docker tag docsense-backend:${VERSION} registry.example.com/docsense-backend:${VERSION}
docker push registry.example.com/docsense-backend:${VERSION}

# 2. Build frontend image
cd client
docker build -t docsense-frontend:${VERSION} -f Dockerfile .
docker tag docsense-frontend:${VERSION} registry.example.com/docsense-frontend:${VERSION}
docker push registry.example.com/docsense-frontend:${VERSION}

# 3. Tag as latest (only after successful deployment)
# docker tag docsense-backend:${VERSION} registry.example.com/docsense-backend:latest
```

### Step 3: Deploy Backend

Deploy backend services with zero-downtime rolling update.

**Using Kubernetes**:
```bash
# 1. Update deployment manifest with new version
sed -i "s/docsense-backend:.*/docsense-backend:${VERSION}/" k8s/backend-deployment.yaml

# 2. Apply deployment
kubectl apply -f k8s/backend-deployment.yaml

# 3. Watch rollout status
kubectl rollout status deployment/docsense-backend -n production

# 4. Verify pods are running
kubectl get pods -n production -l app=docsense-backend
```

**Using Docker Compose**:
```bash
# 1. Update docker-compose.prod.yml with new version
sed -i "s/docsense-backend:.*/docsense-backend:${VERSION}/" docker-compose.prod.yml

# 2. Pull new images
docker-compose -f docker-compose.prod.yml pull backend

# 3. Restart backend with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend

# 4. Verify backend is healthy
curl https://api.example.com/health
```

### Step 4: Deploy Frontend

Deploy frontend after backend is confirmed healthy.

**Using Kubernetes**:
```bash
# 1. Update deployment manifest
sed -i "s/docsense-frontend:.*/docsense-frontend:${VERSION}/" k8s/frontend-deployment.yaml

# 2. Apply deployment
kubectl apply -f k8s/frontend-deployment.yaml

# 3. Watch rollout
kubectl rollout status deployment/docsense-frontend -n production
```

**Using Docker Compose**:
```bash
# 1. Pull new images
docker-compose -f docker-compose.prod.yml pull frontend

# 2. Restart frontend
docker-compose -f docker-compose.prod.yml up -d --no-deps frontend
```

### Step 5: Smoke Tests

Run smoke tests to verify deployment.

```bash
# 1. Health check
curl -f https://api.example.com/health || echo "Health check failed"

# 2. API version check
curl https://api.example.com/version | jq '.version'

# 3. Frontend loads
curl -f https://app.example.com/ || echo "Frontend failed"

# 4. Database connectivity
curl https://api.example.com/health/db | jq '.status'

# 5. AI provider connectivity
curl https://api.example.com/health/ai | jq '.providers'

# 6. Projection health
curl https://api.example.com/health/projections | jq '.projections[] | {name, status}'
```

### Step 6: Monitor Metrics

Watch key metrics for first 30 minutes after deployment.

**Metrics to Monitor**:
- Response time (p50, p95, p99)
- Error rate (5xx responses)
- Request rate
- Database connection pool utilization
- AI API latency
- Projection lag
- Memory and CPU usage

**Tools**:
- Prometheus/Grafana dashboards
- Application logs: `kubectl logs -f deployment/docsense-backend -n production`
- Error tracking (Sentry/Rollbar)

### Step 7: Verify Projections

Ensure read models are updating correctly.

```bash
# 1. Check projection health
curl https://api.example.com/health/projections | jq '.'

# 2. Check for failed projections
curl https://api.example.com/admin/projections/status | jq '.failed_projections'

# 3. Monitor projection lag
watch -n 5 'curl -s https://api.example.com/health/projections | jq ".projections[] | {name, lag}"'
```

## Post-Deployment

### Success Criteria

- [ ] All pods/containers running and healthy
- [ ] Health checks passing for 30 minutes
- [ ] Error rate < 1%
- [ ] Response time within SLA (p95 < 1s)
- [ ] No projection failures
- [ ] User-facing functionality verified manually
- [ ] No critical errors in logs

### Rollback Procedure

If deployment fails, rollback immediately:

**Kubernetes**:
```bash
# Rollback to previous version
kubectl rollout undo deployment/docsense-backend -n production
kubectl rollout undo deployment/docsense-frontend -n production

# Verify rollback
kubectl rollout status deployment/docsense-backend -n production
```

**Docker Compose**:
```bash
# Revert to previous version
git checkout HEAD~1 docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

**Database Rollback** (if migration was applied):
```bash
# Restore from backup
psql -h $DB_HOST -U $DB_USER -d $DB_NAME < backup_YYYYMMDD_HHMMSS.sql

# OR apply rollback migration
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/rollback_YYYYMMDD.sql
```

### Communication

- [ ] Notify team in Slack #deployments channel
- [ ] Update status page (if applicable)
- [ ] Document any issues encountered
- [ ] Schedule post-mortem if rollback was needed

## Troubleshooting

### Common Issues

**Issue: Configuration validation fails at startup**
```
Error: Configuration validation failed: At least one AI provider API key must be configured
```
**Solution**: Verify AI provider API keys are set correctly in secrets management.

**Issue: Database connection fails**
```
Error: could not translate host name "db.example.com" to address
```
**Solution**: Verify DATABASE_URL is correct and database is accessible from application network.

**Issue: CORS errors in browser console**
```
Access to fetch at 'https://api.example.com' from origin 'https://app.example.com' has been blocked by CORS policy
```
**Solution**: Verify CORS_ORIGINS includes frontend domain.

**Issue: Projection lag increasing**
```
DocumentProjection lag: 1500 events
```
**Solution**: Check projection_failures table for errors, may need manual replay.

### Getting Help

- Check application logs: `kubectl logs -f deployment/docsense-backend`
- Check database logs: `kubectl logs -f statefulset/postgresql`
- Review monitoring dashboards
- Contact on-call engineer
- Escalate to platform team if infrastructure issue

## Related Documentation

- [Environment Variables Reference](../deployment/environment-variables.md)
- [Event Store Schema](../database/event_store_schema.sql)
- [Projection Failure Handling](../changes/2025-12-12-projection-failure-handling-fix.md)
- [Production Readiness Review](../analysis/production-readiness-review.md)
