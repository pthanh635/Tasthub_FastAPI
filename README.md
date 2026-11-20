# TaskHub API

TaskHub is a production-ready, multi-tenant Task & Project Management REST API built with **FastAPI**, **SQLAlchemy 2.x (Async ORM)**, **PostgreSQL (`asyncpg`)**, **Redis**, and **Pydantic v2**.

---

## 🚀 Features

- **Architecture & Design**: Clean Layered Architecture (`Routers -> Services -> Repositories -> Models/Schemas`) with explicit Dependency Injection.
- **Authentication & Security**:
  - JWT Authentication (Access + Refresh token rotation).
  - Reuse detection for refresh tokens: atomically revokes all active sessions if a revoked token is used.
  - Role-Based Access Control (RBAC):
    - **Global Roles**: `ADMIN`, `MEMBER`.
    - **Workspace Roles**: `OWNER`, `ADMIN`, `EDITOR`, `VIEWER`.
- **Database & Migrations**:
  - Fully asynchronous database operations with `asyncpg` and SQLAlchemy 2.0 async sessions.
  - Database schema versioning with Alembic migrations.
- **High Performance Caching**:
  - Redis cache layer with automatic cache invalidation on write mutations.
  - Path-scoped cache for public endpoints with `X-Cache` diagnostic headers (`HIT`, `MISS`, `BYPASS`).
  - Automatic reconnection backoff and socket timeouts preventing API blocking.
- **Structured Logging & Diagnostics**:
  - Request tracing headers (`X-Request-ID`, `X-Process-Time-Ms`).
  - Container/Cloud-ready structured JSON logging format with UTC timestamps.
- **Background Tasks & Queue**:
  - Asynchronous background task runner with graceful shutdown support.
  - Background email notifications and audit event logging.
- **Containerization**:
  - Multi-stage Docker build for minimal image size and secure non-root execution (`appuser:1001`).
  - Docker Compose setup orchestrating API, PostgreSQL, and Redis.
- **Interactive Documentation**:
  - OpenAPI 3.1 schema, Swagger UI (`/docs`), and ReDoc (`/redoc`) with toggleable `DOCS_ENABLED`.

---

## 📂 Project Structure

```text
taskhub/
├── alembic/                      # Database migration scripts
│   └── versions/                 # Migration revision files
├── app/
│   ├── api/                      # API presentation layer
│   │   └── v1/
│   │       ├── dependencies.py   # FastAPI dependency injections
│   │       └── routers/          # Endpoints: auth, users, workspaces, projects, tasks
│   ├── core/                     # Application configurations & foundational components
│   │   ├── cache.py              # Redis cache adapter
│   │   ├── config.py             # Pydantic Settings & multi-env loader
│   │   ├── constants.py          # Enums, defaults, and system constants
│   │   ├── database.py           # Async SQLAlchemy engine & session factory
│   │   ├── exceptions.py         # Custom domain exceptions
│   │   ├── logging.py            # Structured JSON formatter and setup
│   │   ├── messages.py           # Centralized domain and error messages
│   │   ├── middleware.py         # Request context and Redis cache middleware
│   │   ├── openapi.py            # OpenAPI metadata and Swagger configuration
│   │   ├── policies.py           # RBAC permission matrix
│   │   ├── security.py           # Password hashing (bcrypt) & JWT utilities
│   │   └── tasks.py              # Background task queue & worker jobs
│   ├── models/                   # SQLAlchemy declarative ORM models
│   ├── repositories/             # Data access repository layer
│   ├── schemas/                  # Pydantic data validation schemas
│   ├── services/                 # Business logic service layer
│   └── main.py                   # FastAPI application factory & lifespan
├── tests/                        # Automated test suite (67 test cases)
├── Dockerfile                    # Multi-stage container build definition
├── docker-compose.yml            # Local development orchestration (App + DB + Redis)
├── requirements.txt              # Production and development dependencies
├── pyproject.toml                # Project configurations (Ruff, Mypy)
└── pytest.ini                    # Pytest test discovery & execution settings
```

---

## 🛠️ Quick Start

### Option 1: Run with Docker Compose (Recommended)

1. **Clone repository and setup environment variables:**
   ```bash
   cp .env.example .env
   ```

2. **Start all services (App, PostgreSQL, Redis):**
   ```bash
   docker compose up --build -d
   ```

3. **Check logs and status:**
   ```bash
   docker compose logs -f app
   ```

4. Access the API documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Local Development Setup

1. **Prerequisites:**
   - Python 3.11+
   - PostgreSQL running on port `5432`
   - Redis running on port `6379`

2. **Create virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 🧪 Testing & Code Quality

Run tests, type checks, and linters:

```bash
# Run full pytest test suite (67 test cases)
python -m pytest -v

# Run code style and linting checks
python -m ruff check .

# Run static type checking
python -m mypy app
```

---

## ⚙️ Environment Configuration

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | Application environment (`development`, `testing`, `staging`, `production`) | `development` |
| `APP_NAME` | Name displayed in OpenAPI documentation | `TaskHub API` |
| `DOCS_ENABLED` | Enable or disable Swagger UI & ReDoc | `true` |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis server connection string | `redis://localhost:6379/0` |
| `CACHE_TTL_SECONDS` | Cache expiration time in seconds | `30` |
| `CACHE_PUBLIC_PATHS`| Comma-separated list of public routes enabled for caching | `/api/v1/workspaces, ...` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens (min 32 chars) | Required |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `LOG_JSON_FORMAT` | Enable structured JSON logging format | `true` |
