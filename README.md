<p align="center">
  <h1 align="center">🛒 Order Processing & Notification System</h1>
  <p align="center">
    A production-ready Django REST API for e-commerce order management with integrated payments and real-time notifications
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-green?style=flat-square&logo=django" alt="Django 6.0">
  <img src="https://img.shields.io/badge/DRF-3.16-red?style=flat-square&logo=django" alt="DRF">
  <img src="https://img.shields.io/badge/Celery-5.6-37814A?style=flat-square&logo=celery" alt="Celery">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker" alt="Docker">
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Data Models](#-data-models)
- [API Reference](#-api-reference)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)

---

## 🎯 Overview

A comprehensive order processing system built with Django REST Framework that handles the complete e-commerce order lifecycle—from user registration and product browsing to payment processing and multi-channel notifications.

### Key Capabilities

- **User Management** — JWT-based authentication with role-based access control
- **Order Processing** — Full order lifecycle with inventory management
- **Payment Integration** — UroPay UPI payment gateway with webhook support
- **Notifications** — Asynchronous email and SMS notifications via Celery
- **API Documentation** — Auto-generated OpenAPI 3.0 specs with Swagger UI

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 **JWT Authentication** | Secure token-based auth with refresh tokens |
| 👥 **Role-Based Access** | Customer, Admin, and Super Admin roles |
| 📦 **Order Management** | Create, view, and track orders with status updates |
| 💳 **UPI Payments** | UroPay integration with QR codes and webhooks |
| 📧 **Email Notifications** | HTML templates for order confirmations |
| 📱 **SMS Notifications** | Twilio-ready SMS adapter |
| 🔄 **Async Processing** | Celery workers for background tasks |
| 📄 **API Documentation** | Swagger UI and ReDoc |
| 🐳 **Docker Ready** | Full containerization with compose |
| ✅ **Test Coverage** | Comprehensive pytest test suite |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                               │
│                    (Web App / Mobile App / API Client)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Django REST Framework                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  Accounts   │  │   Orders    │  │  Payments   │  │  Notifications  │ │
│  │   Module    │  │   Module    │  │   Module    │  │     Module      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
        │                   │                │                │
        ▼                   ▼                ▼                ▼
┌──────────────┐    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │    │    Redis     │  │   UroPay    │  │ Email/SMS    │
│   Database   │    │   (Broker)   │  │   Gateway   │  │  Providers   │
└──────────────┘    └──────────────┘  └──────────────┘  └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    Celery    │
                    │   Workers    │
                    └──────────────┘
```

---

## 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| **Framework** | Django 6.0, Django REST Framework 3.16 |
| **Database** | PostgreSQL 16 |
| **Cache/Broker** | Redis 7 |
| **Task Queue** | Celery 5.6 |
| **Authentication** | djangorestframework-simplejwt |
| **Documentation** | drf-spectacular (OpenAPI 3.0) |
| **Testing** | pytest, pytest-django, factory_boy |
| **Containerization** | Docker, Podman Compose |

---

## 📊 Data Models

### Entity Relationship Diagram

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│      User        │       │      Order       │       │    OrderItem     │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ id (PK)          │
│ username         │◄──────│ user_id (FK)     │◄──────│ order_id (FK)    │
│ email            │   1:N │ status           │   1:N │ product_id       │
│ phone_number     │       │ address          │       │ product_name     │
│ notify_email     │       │ total_amount     │       │ price            │
│ notify_sms       │       │ created_at       │       │ quantity         │
│ email_verified   │       │ updated_at       │       └──────────────────┘
│ sms_verified     │       └──────────────────┘
└──────────────────┘               │
                                   │ 1:1
                                   ▼
                           ┌──────────────────┐       ┌──────────────────┐
                           │     Payment      │       │   Notification   │
                           ├──────────────────┤       ├──────────────────┤
                           │ id (PK)          │       │ id (PK)          │
                           │ order_id (FK)    │       │ order_id (FK)    │
                           │ amount           │       │ channel          │
                           │ status           │       │ status           │
                           │ uro_pay_order_id │       │ payload (JSON)   │
                           │ upi_string       │       │ attempts         │
                           │ qr_code          │       │ sent_at          │
                           │ reference_number │       │ error_message    │
                           └──────────────────┘       └──────────────────┘

┌──────────────────┐       ┌──────────────────┐
│     Product      │       │  WebhookEvent    │
├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │
│ name             │       │ webhook_id       │
│ price            │       │ payload (JSON)   │
│ inventory        │       │ received_at      │
└──────────────────┘       └──────────────────┘
```

### Model Details

#### User Model
Extended from Django's `AbstractUser` with notification preferences:

| Field | Type | Description |
|-------|------|-------------|
| `username` | CharField | Unique username |
| `email` | EmailField | User email address |
| `phone_number` | CharField | Optional phone for SMS |
| `notify_email` | Boolean | Email notification preference |
| `notify_sms` | Boolean | SMS notification preference |
| `email_verified` | Boolean | Email verification status |
| `sms_verified` | Boolean | SMS verification status |

**Roles:**
- **Customer**: `is_staff=False`, `is_superuser=False`
- **Admin**: `is_staff=True`, `is_superuser=False`
- **Super Admin**: `is_staff=True`, `is_superuser=True`

#### Order Model

| Field | Type | Description |
|-------|------|-------------|
| `user` | ForeignKey | Associated user |
| `status` | CharField | Order status (see below) |
| `address` | TextField | Shipping address |
| `total_amount` | Decimal | Calculated order total |
| `created_at` | DateTime | Order creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

**Order Statuses:**
```
PENDING → PAID → PROCESSING → SHIPPED → DELIVERED
                     ↓
                 CANCELLED
```

#### Payment Model

| Field | Type | Description |
|-------|------|-------------|
| `order` | OneToOneField | Associated order |
| `amount` | Decimal | Payment amount |
| `status` | CharField | `INITIATED` / `SUCCESS` / `FAILED` |
| `uro_pay_order_id` | CharField | UroPay transaction ID |
| `upi_string` | TextField | UPI payment string |
| `qr_code` | TextField | Base64 QR code image |
| `reference_number` | CharField | UPI reference number |

#### Notification Model

| Field | Type | Description |
|-------|------|-------------|
| `order` | ForeignKey | Associated order |
| `channel` | CharField | `EMAIL` / `SMS` / `WEBHOOK` |
| `status` | CharField | `PENDING` / `SENT` / `FAILED` |
| `payload` | JSONField | Notification data |
| `attempts` | Integer | Retry count |
| `unique_key` | CharField | Idempotency key |

---

## 📡 API Reference

### Base URL
```
http://localhost:8000/api/
```

### Authentication
All endpoints (except registration and login) require JWT authentication:
```
Authorization: Bearer <access_token>
```

---

### 🔐 Accounts API

#### Register User
```http
POST /api/accounts/register/
```

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securePassword123",
  "phone_number": "+1234567890",
  "notify_email": true,
  "notify_sms": false
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com"
}
```

---

#### Login
```http
POST /api/accounts/login/
```

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

#### Refresh Token
```http
POST /api/accounts/token/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

### 📦 Orders API

#### List Products
```http
GET /api/orders/products/
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page (max: 100) |

**Response:** `200 OK`
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/orders/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Wireless Headphones",
      "price": "99.99"
    }
  ]
}
```

---

#### Create Order
```http
POST /api/orders/create/
```

**Request Body:**
```json
{
  "address": "123 Main St, City, Country 12345",
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    },
    {
      "product_id": 3,
      "quantity": 1
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "order_id": 42,
  "total_amount": "299.97",
  "address": "123 Main St, City, Country 12345"
}
```

---

#### List My Orders
```http
GET /api/orders/
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 10 | Items per page (max: 100) |

**Response:** `200 OK`
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "status": "PENDING",
      "total_amount": "299.97",
      "address": "123 Main St, City, Country 12345",
      "items": [
        {
          "product_id": 1,
          "product_name": "Wireless Headphones",
          "price": "99.99",
          "quantity": 2
        }
      ],
      "created_at": "2026-01-20T10:30:00Z"
    }
  ]
}
```

---

#### Get Order Details
```http
GET /api/orders/{id}/
```

**Response:** `200 OK`
```json
{
  "id": 42,
  "status": "PAID",
  "total_amount": "299.97",
  "address": "123 Main St, City, Country 12345",
  "items": [...],
  "created_at": "2026-01-20T10:30:00Z",
  "updated_at": "2026-01-20T10:35:00Z"
}
```

---

### 💳 Payments API

#### Generate Payment (Step 1)
```http
POST /api/payments/create/
```

**Request Body:**
```json
{
  "order_id": 42,
  "vpa": "customer@upi",
  "vpaName": "Customer Name",
  "customerName": "John Doe",
  "customerEmail": "john@example.com",
  "transactionNote": "Payment for Order #42"
}
```

**Response:** `201 Created`
```json
{
  "order_id": 42,
  "amount": "299.97",
  "status": "INITIATED",
  "uro_pay_order_id": "URO123456789",
  "upi_string": "upi://pay?pa=merchant@upi&pn=Store&am=299.97...",
  "qr_code": "data:image/png;base64,iVBORw0KGgo..."
}
```

---

#### Confirm Payment (Step 2)
```http
POST /api/payments/confirm/
```

**Request Body:**
```json
{
  "order_id": 42,
  "referenceNumber": "UPI123456789012"
}
```

**Response:** `200 OK`
```json
{
  "order_id": 42,
  "amount": "299.97",
  "status": "SUCCESS",
  "reference_number": "UPI123456789012"
}
```

---

#### Payment Webhook (UroPay → Server)
```http
POST /api/payments/webhook/
```

> ⚠️ This endpoint is called by UroPay servers. Signature verification is performed automatically.

---

### 📖 API Documentation

| Endpoint | Description |
|----------|-------------|
| `/api/docs/` | Swagger UI interactive documentation |
| `/api/redoc/` | ReDoc documentation |
| `/api/schema/` | OpenAPI 3.0 JSON schema |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Docker/Podman (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/order-processing-system.git
   cd order-processing-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Start Celery worker** (in a new terminal)
   ```bash
   celery -A config worker -l INFO
   ```

### Docker Setup

```bash
# Build and start all services
make build
make up

# View logs
make logs

# Run migrations
make migrate

# Create superuser
make createsuperuser

# Stop services
make down
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `True` |
| `SECRET_KEY` | Django secret key | — |
| `POSTGRES_DB` | Database name | `order_processing` |
| `POSTGRES_USER` | Database user | `order_user` |
| `POSTGRES_PASSWORD` | Database password | — |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `CELERY_BROKER_URL` | Redis broker URL | `redis://localhost:6379/0` |
| `UROPAY_API_KEY` | UroPay API key | — |
| `UROPAY_SECRET` | UroPay secret | — |
| `EMAIL_HOST_USER` | SMTP username | — |
| `EMAIL_HOST_PASSWORD` | SMTP password | — |
| `DEFAULT_FROM_EMAIL` | Sender email | — |

---

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific app tests
pytest accounts/
pytest orders/
pytest payments/
pytest notifications/

# Run with verbose output
pytest -v
```

### Test Structure
```
├── conftest.py              # Shared fixtures
├── accounts/test_accounts.py
├── orders/test_orders.py
├── payments/test_payments.py
└── notifications/test_notifications.py
```

---

## 🐳 Deployment

### Production Docker Compose

```bash
# Start production services
make prod-up

# Stop production services
make prod-down
```

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure strong `SECRET_KEY`
- [ ] Set up SSL/TLS certificates
- [ ] Configure production database
- [ ] Set up Redis persistence
- [ ] Configure email provider (SMTP)
- [ ] Set up monitoring and logging
- [ ] Configure UroPay production credentials
- [ ] Run `collectstatic`

---

## 📁 Project Structure

```
Order_Processing_Notification_system/
├── config/                     # Project configuration
│   ├── settings.py            # Django settings
│   ├── urls.py                # Root URL configuration
│   ├── celery.py              # Celery configuration
│   ├── middleware.py          # Custom middleware
│   └── pagination.py          # DRF pagination classes
│
├── accounts/                   # User management app
│   ├── models.py              # Custom User model
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # Registration, Login views
│   └── urls.py                # Account endpoints
│
├── orders/                     # Order management app
│   ├── models.py              # Order, OrderItem, Product
│   ├── api/
│   │   ├── serializers.py     # Order serializers
│   │   ├── views.py           # Order CRUD views
│   │   └── urls.py            # Order endpoints
│   └── services/
│       └── order_creation.py  # Order business logic
│
├── payments/                   # Payment processing app
│   ├── models.py              # Payment, WebhookEvent
│   ├── api/
│   │   ├── serializers.py     # Payment serializers
│   │   ├── views.py           # Payment views
│   │   └── urls.py            # Payment endpoints
│   ├── clients/               # UroPay client
│   └── services/
│       └── payment_service.py # Payment business logic
│
├── notifications/              # Notification app
│   ├── models.py              # Notification model
│   ├── tasks.py               # Celery tasks
│   ├── adapters/
│   │   ├── email.py           # Email adapter
│   │   └── sms.py             # SMS adapter
│   └── templates/
│       └── notifications/     # Email templates
│
├── docker-compose.yml          # Development compose
├── docker-compose.prod.yml     # Production compose
├── Dockerfile                  # Container definition
├── Makefile                    # Automation commands
├── requirements.txt            # Python dependencies
└── pytest.ini                  # Test configuration
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where applicable
- Write docstrings for classes and functions
- Maintain test coverage above 80%

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ using Django REST Framework
</p>
