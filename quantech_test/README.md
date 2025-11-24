# Cloud Licensing Management System

> A robust, production-ready cloud licensing management system that enforces application and execution quotas for multi-tenant environments.

[![Django](https://img.shields.io/badge/Django-5.0.1-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14.0-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-red.svg)](https://redis.io/)

## 🚀 Features

✅ **License-Based Authentication**: JWT token authentication with server-side signature verification
✅ **Application Quota Enforcement**: Atomic enforcement of `maxApps` constraint per tenant
✅ **Execution Quota Management**: 24-hour sliding window for execution limits
✅ **Race Condition Prevention**: Distributed locks for concurrent request handling
✅ **Real-time Monitoring**: Comprehensive metrics and statistics
✅ **Production Ready**: Docker Compose deployment, PostgreSQL + Redis

## 📋 Challenge Requirements Compliance

| Requirement | Implementation | Status |
|------------|----------------|--------|
| `POST /apps/register` | [applications/urls.py:14](src/applications/urls.py#L14) | ✅ |
| `POST /jobs/start` | [jobs/urls.py:15](src/jobs/urls.py#L15) | ✅ |
| `POST /jobs/finish` | [jobs/urls.py:16](src/jobs/urls.py#L16) | ✅ |
| maxApps enforcement | [quotas.py:215](src/utility/quotas.py#L215) | ✅ |
| 24h sliding window | [quotas.py:86](src/utility/quotas.py#L86) | ✅ |
| Race condition prevention | [quotas.py:98](src/utility/quotas.py#L98) (Redis locks) | ✅ |
| JWT signature verification | [auth_jwt.py:79](src/utility/auth_jwt.py#L79) | ✅ |
| Docker Compose deployment | [docker-compose.yml](docker-compose.yml) | ✅ |

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ JWT Token
       ▼
┌─────────────────────────────────┐
│  Django + DRF (Gunicorn)        │
│  ┌──────────┐  ┌──────────┐   │
│  │  Auth    │  │  Quota   │   │
│  │ Backend  │  │ Service  │   │
│  └──────────┘  └──────────┘   │
└────┬─────────────────┬──────────┘
     │                 │
     ▼                 ▼
┌──────────┐      ┌──────────┐
│PostgreSQL│      │  Redis   │
│ (Licenses│      │(Quotas + │
│  + Jobs) │      │  Locks)  │
└──────────┘      └──────────┘
```

### Technology Stack

- **Backend**: Django 5.0.1 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Task Processing**: Celery 5.3.4 + Celery Beat
- **Web Server**: Gunicorn 21.2.0
- **Containerization**: Docker + Docker Compose

## 🎯 Quick Start

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Port 8000 available

### One-Command Deployment

```bash
docker compose up --build
```

The system will be available at **http://localhost:8000**

### Services

- **web**: Django API (port 8000)
- **db**: PostgreSQL database
- **redis**: Redis cache and queue
- **celery**: Background task worker
- **celery_beat**: Scheduled task processor

## 📡 API Endpoints

### Public Endpoints (Challenge Requirements)

#### 1. Register Application
```http
POST /api/apps/register
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "name": "My Application",
  "description": "Optional description"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "My Application",
  "description": "Optional description",
  "is_active": true,
  "created_at": "2025-11-24T10:00:00Z"
}
```

**Error (403 Forbidden - Max Apps Reached):**
```json
{
  "error": "Maximum number of applications reached",
  "max_apps": 5,
  "current_count": 5
}
```

---

#### 2. Start Job Execution
```http
POST /api/jobs/start
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "application_id": "uuid",
  "name": "Job Name",
  "description": "Optional",
  "metadata": {}
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "application_id": "uuid",
  "name": "Job Name",
  "status": "RUNNING",
  "started_at": "2025-11-24T10:00:00Z"
}
```

**Error (429 Too Many Requests - Quota Exceeded):**
```json
{
  "error": "Execution quota exceeded",
  "max_executions_per_24h": 1000,
  "current_count": 1000,
  "message": "Execution quota exceeded: 1000/1000 executions in last 24h"
}
```

---

#### 3. Finish Job Execution
```http
POST /api/jobs/finish
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "job_id": "uuid",
  "status": "COMPLETED",
  "result": {},
  "error_message": "",
  "cpu_usage": 45.5,
  "memory_usage": 512
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "COMPLETED",
  "started_at": "2025-11-24T10:00:00Z",
  "finished_at": "2025-11-24T10:05:30Z",
  "execution_time": 330
}
```

### Additional Endpoints

- `GET /api/applications/` - List applications
- `GET /api/jobs/` - List jobs
- `GET /api/jobs/statistics/` - Job statistics
- `GET /api/executions/window/` - Execution window details
- `GET /api/applications/metrics/` - Application metrics

See full API documentation in [Postman Collection](Licensing_API.postman_collection.json)

## 🧪 Testing

### Import Postman Collection

1. Open Postman
2. Import `Licensing_API.postman_collection.json`
3. Update `base_url` variable if needed (default: `http://localhost:8000/api`)

### Test Scenarios Included

1. **Authentication**: Generate JWT tokens
2. **Application Registration**: Test `maxApps` enforcement
3. **Job Execution**: Test 24-hour sliding window
4. **Race Conditions**: Concurrent request tests
5. **Security**: Invalid token tests

### Running Tests

#### Concurrent Testing (Race Conditions)
1. Open Postman Collection Runner
2. Select "Concurrent Job Start" or "Concurrent App Register"
3. Set iterations to 10
4. Run in parallel
5. Verify quota enforcement

#### Load Testing
```bash
# Using Apache Bench
ab -n 1000 -c 50 -H "Authorization: Bearer <token>" \
   -p job.json -T application/json \
   http://localhost:8000/api/jobs/start
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256

# Database
POSTGRES_DB=quantech
POSTGRES_USER=quantech_user
POSTGRES_PASSWORD=strong-password-here
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

## 📁 Project Structure

```
quantech_test/
├── src/
│   ├── applications/          # Application registration
│   │   ├── models.py          # Application, ApplicationMetrics
│   │   ├── serializers.py     # DRF serializers
│   │   ├── views.py           # ApplicationRegisterAPIView
│   │   └── urls.py            # /apps/register endpoint
│   ├── jobs/                  # Job execution
│   │   ├── models.py          # Job, JobExecution, JobStatus
│   │   ├── serializers.py     # Job serializers
│   │   ├── views.py           # JobStartAPIView, JobFinishAPIView
│   │   └── urls.py            # /jobs/start, /jobs/finish
│   ├── licenses/              # License management
│   │   ├── models.py          # License, LicenseToken
│   │   └── views.py           # License CRUD
│   ├── utility/               # Core services
│   │   ├── auth_jwt.py        # JWT authentication backend
│   │   ├── quotas.py          # QuotaService with Redis locks
│   │   └── urls.py            # Utility endpoints
│   ├── user/                  # User management
│   └── src/
│       ├── settings.py        # Django settings
│       ├── urls.py            # Main URL config
│       └── celery.py          # Celery config
├── docker-compose.yml         # Service orchestration
├── Dockerfile                 # Application container
├── requirements.txt           # Python dependencies
├── TECHNICAL_ANALYSIS.md      # Detailed technical documentation
├── Licensing_API.postman_collection.json  # API tests
└── README.md                  # This file
```

## 🔒 Key Implementation Details

### Race Condition Prevention

**Problem**: Concurrent requests can bypass quota limits

**Solution**: Redis distributed locks with atomic check-and-set

```python
# Atomic execution quota check (utility/quotas.py:86)
lock = redis.lock(f"lock:executions:{tenant_id}", timeout=5)
with lock:
    current_count = get_execution_count(tenant_id)
    if current_count >= max_executions:
        return False, current_count, "Quota exceeded"
    redis.zadd(key, {job_id: timestamp})
    return True, current_count + 1, None
```

### Sliding Window with Redis

**Implementation**: Redis Sorted Sets (ZSET)

```python
# Add execution
redis.zadd(f"executions:{tenant_id}", {job_id: timestamp})

# Count within 24h window
now = time.time()
min_time = now - 86400  # 24 hours ago
count = redis.zcount(f"executions:{tenant_id}", min_time, now)

# Auto-cleanup old executions
redis.zremrangebyscore(key, '-inf', min_time)
```

### JWT Security

```python
# Decode with signature verification (utility/auth_jwt.py:79)
payload = jwt.decode(
    token,
    settings.JWT_SECRET_KEY,
    algorithms=['HS256']  # Only allow HS256
)

# Validate license status and expiration
if license.status != 'ACTIVE':
    raise AuthenticationFailed('License is not active')
if now > license.valid_to:
    raise AuthenticationFailed('License has expired')
```

## 📊 Monitoring & Observability

### Logs

All critical operations are logged:

```python
# Execution quota checks
logger.info(f"Job {job_id} started. Executions: {count}/{max}")
logger.warning(f"Tenant {tenant_id} quota exceeded: {count}/{max}")

# Application registration
logger.info(f"Application {app_id} registered. Apps: {count}/{max}")
```

### Metrics to Track

- Lock acquisition time (p50, p95, p99)
- Quota check latency
- Application/execution count per tenant
- Redis operation performance
- API endpoint response times

## 🛠️ Troubleshooting

### Redis Connection Issues

```bash
# Check Redis is running
docker compose ps redis

# Restart Redis
docker compose restart redis
```

### Database Migration Issues

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Or rebuild
docker compose down -v
docker compose up --build
```

## 🚀 Production Deployment

### Security Checklist

- [ ] Change `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use strong database passwords
- [ ] Enable HTTPS (reverse proxy with Nginx/Caddy)
- [ ] Configure CORS properly
- [ ] Set up database backups
- [ ] Enable Redis persistence (RDB + AOF)
- [ ] Set up monitoring (Prometheus + Grafana)

### Scaling Recommendations

**Horizontal Scaling**:
```yaml
services:
  web:
    deploy:
      replicas: 3
```

**Database**: Primary-replica setup, connection pooling
**Redis**: Sentinel for HA, Cluster for horizontal scaling

## 📚 Documentation

- **Technical Analysis**: [TECHNICAL_ANALYSIS.md](TECHNICAL_ANALYSIS.md) - Detailed architecture decisions and trade-offs
- **API Collection**: [Licensing_API.postman_collection.json](Licensing_API.postman_collection.json) - Complete API test suite
- **Challenge Reference**: https://github.com/ranoquantech/licensing-cloud-challenge

## 📄 License

MIT License

## 👥 Authors

Built for the Licensing Cloud Challenge

---

**Development Time**: 5 days
**Stack**: Django + PostgreSQL + Redis + Docker
**Focus**: Security, Race Condition Prevention, Sliding Window Accuracy
