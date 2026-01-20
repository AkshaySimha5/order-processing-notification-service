# Order Processing Notification System - Docker Setup

## Quick Start

### Prerequisites
- Docker/Podman and Docker Compose/Podman-Compose installed
- Copy `.env.example` to `.env` and configure your environment variables

### Start All Services (Development)

```bash
# Build and start all services
make up

# Or using podman-compose directly
podman-compose up -d
```

### Services Overview

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| PostgreSQL | smart_order_postgres | 5432 | Database |
| Redis | smart_order_redis | 6380 (external) | Celery message broker |
| Django Web | smart_order_web | 8000 | Web application |
| Celery Worker | smart_order_celery_worker | - | Background task processor |
| Celery Beat | smart_order_celery_beat | - | Scheduled tasks |

### Common Commands

```bash
# View all container logs
make logs

# View specific service logs
make logs-web
make logs-celery

# Run Django shell
make shell

# Run migrations
make migrate

# Create migrations
make makemigrations

# Create superuser
make createsuperuser

# Run tests
make test

# Stop all services
make down

# Clean up everything (including volumes)
make clean
```

### Production Deployment

```bash
# Start in production mode (uses gunicorn)
make prod-up

# Stop production services
make prod-down
```

### Running Only Database/Redis (for local development)

If you want to run Django locally but use containerized database:

```bash
# Start only PostgreSQL
make db-only

# Start only Redis
make redis-only
```

Then run Django locally with:
```bash
python manage.py runserver
```

### Environment Variables

Key environment variables (set in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Django debug mode | `True` |
| `SECRET_KEY` | Django secret key | Required |
| `POSTGRES_DB` | Database name | `order_processing` |
| `POSTGRES_USER` | Database user | `order_user` |
| `POSTGRES_PASSWORD` | Database password | `order_password` |
| `POSTGRES_HOST` | Database host | `db` (container) / `localhost` (local) |
| `CELERY_BROKER_URL` | Redis broker URL | `redis://redis:6379/0` (container) |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                           │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐│
│  │  PostgreSQL │  │    Redis    │  │      Django Web      ││
│  │   (db:5432) │  │ (redis:6379)│  │      (web:8000)      ││
│  └─────────────┘  └─────────────┘  └──────────────────────┘│
│         │                │                    │             │
│         │                │                    │             │
│  ┌──────┴────────────────┴────────────────────┴───────────┐│
│  │              Celery Worker & Beat                      ││
│  │         (Background Task Processing)                   ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
              │                    │
              ▼                    ▼
         Host:5432           Host:8000
         Host:6380
```

### Troubleshooting

**Port conflicts:**
- If port 6379 is in use (local Redis), the container uses 6380 externally
- If port 5432 is in use, stop your local PostgreSQL or change the port in docker-compose.yml

**Container not starting:**
```bash
# Check container logs
podman logs smart_order_web

# Check all containers status
podman ps -a --filter "name=smart_order"
```

**Database connection issues:**
- Make sure `POSTGRES_HOST=db` when running in containers
- Make sure `POSTGRES_HOST=localhost` when running Django locally with containerized DB
