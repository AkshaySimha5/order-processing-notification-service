.PHONY: help build up down logs shell migrate makemigrations createsuperuser test clean prod-up prod-down

# Default target
help:
	@echo "Order Processing Notification System - Docker Commands"
	@echo ""
	@echo "Development Commands:"
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services (development)"
	@echo "  make down           - Stop all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make logs-web       - View logs from web service only"
	@echo "  make logs-celery    - View logs from celery worker"
	@echo "  make shell          - Open Django shell in web container"
	@echo "  make bash           - Open bash shell in web container"
	@echo "  make migrate        - Run database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make createsuperuser - Create Django superuser"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Remove all containers and volumes"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod-up        - Start all services (production)"
	@echo "  make prod-down      - Stop production services"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-only        - Start only the database service"
	@echo "  make redis-only     - Start only the Redis service"

# Build Docker images
build:
	podman-compose build

# Development - Start all services
up:
	podman-compose up -d

# Stop all services
down:
	podman-compose down

# View all logs
logs:
	podman-compose logs -f

# View web logs only
logs-web:
	podman logs -f smart_order_web

# View celery worker logs
logs-celery:
	podman logs -f smart_order_celery_worker

# Open Django shell
shell:
	podman exec -it smart_order_web python manage.py shell

# Open bash shell in web container
bash:
	podman exec -it smart_order_web bash

# Run migrations
migrate:
	podman exec -it smart_order_web python manage.py migrate

# Create migrations (needs root to write files to mounted volume)
makemigrations:
	podman exec -it --user root smart_order_web python manage.py makemigrations

# Create superuser
createsuperuser:
	podman exec -it smart_order_web python manage.py createsuperuser

# Run tests
test:
	podman exec -it smart_order_web python manage.py test

# Clean everything
clean:
	podman-compose down -v
	podman system prune -f

# Production - Start all services
prod-up:
	podman-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Production - Stop services
prod-down:
	podman-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Start only database (useful for local development)
db-only:
	podman-compose up -d db

# Start only Redis (useful for local development)
redis-only:
	podman-compose up -d redis

# Import products (management command)
import-products:
	podman exec -it smart_order_web python manage.py import_products
