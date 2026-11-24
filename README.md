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
  - Database schema versioning with Alembic migrations (`migrate` service runs automatically in Docker Compose).
- **High Performance Caching**:
  - Redis cache layer with automatic cache invalidation on write mutations.
  - Path-scoped cache for public endpoints with `X-Cache` diagnostic headers (`HIT`, `MISS`, `BYPASS`).
  - Automatic reconnection backoff and socket timeouts preventing API blocking.
- **Structured Logging & Diagnostics**:
  - Request tracing headers (`X-Request-ID`, `X-Process-Time-Ms`) propagated via `ContextVar` into every log record.
  - Unified JSON logging across application and Uvicorn loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`).
- **Background Tasks & Queue**:
  - Dependency-injected asynchronous `TaskQueue` (`Depends(get_task_queue)`) with graceful shutdown support.
  - PII-safe background email notifications and enum-typed audit event logging (`AuditAction`, `AuditResource`).
- **Containerization**:
  - Multi-stage Docker build installing runtime-only dependencies (`requirements.txt`) under a non-root user (`appuser:1001`).
  - Docker Compose setup orchestrating PostgreSQL, Redis, automated Alembic migrations (`migrate`), and the API (`app`).
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
│   │       ├── dependencies.py   # FastAPI dependency injections (Auth, DB, TaskQueue)
│   │       └── routers/          # Endpoints: auth, users, workspaces, projects, tasks
│   ├── core/                     # Application configurations & foundational components
│   │   ├── cache.py              # Redis cache adapter
│   │   ├── config.py             # Pydantic Settings & multi-env loader
│   │   ├── constants.py          # Enums, defaults, and system constants
│   │   ├── database.py           # Async SQLAlchemy engine & session factory
│   │   ├── exceptions.py         # Custom domain exceptions
│   │   ├── logging.py            # ContextVar request_id filter & JSONFormatter
│   │   ├── messages.py           # Centralized error and email templates
│   │   ├── middleware.py         # Request context and Redis cache middleware
│   │   ├── openapi.py            # OpenAPI metadata and Swagger configuration
│   │   ├── policies.py           # RBAC permission matrix
│   │   ├── security.py           # Password hashing (bcrypt) & JWT utilities
│   │   ├── seed.py               # Idempotent initial admin/workspace/project seeder
│   │   └── tasks.py              # Async TaskQueue & PII-safe background jobs
│   ├── models/                   # SQLAlchemy declarative ORM models & domain enums
│   ├── repositories/             # Data access repository layer
│   ├── schemas/                  # Pydantic data validation schemas
│   ├── services/                 # Business logic service layer
│   └── main.py                   # FastAPI application factory & lifespan
├── tests/                        # Automated test suite
├── Dockerfile                    # Multi-stage runtime container build
├── docker-compose.yml            # Orchestration (db + redis + migrate + app)
├── requirements.txt              # Production runtime dependencies
├── requirements-dev.txt          # Development, testing, and linting dependencies
├── pyproject.toml                # Project configurations (Ruff, Mypy)
└── pytest.ini                    # Pytest test discovery & execution settings
```

---

## 🛠️ Quick Start

### Option 1: Run with Docker Compose (Recommended)

1. **Create `.env` and configure required secrets:**
   ```bash
   cp .env.example .env
   ```
   Update `.env` with a strong `JWT_SECRET_KEY` (at least 32 characters; `docker compose` enforces `${JWT_SECRET_KEY:?}`) and set `SEED_ADMIN_PASSWORD` (at least 12 characters) if you plan to seed initial admin data.

2. **Build and start all services (`db`, `redis`, `migrate`, `app`):**
   ```bash
   docker compose up --build -d
   ```
   > The `migrate` service automatically runs `python -m alembic upgrade head` once PostgreSQL is healthy, and `app` waits until migrations complete successfully before starting.

3. **Seed initial admin user, default workspace, and project (optional, idempotent):**
   ```bash
   docker compose exec app python -m app.core.seed
   ```

4. **Inspect structured JSON logs:**
   ```bash
   docker compose logs -f app
   ```

5. Access the API documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Local Development Setup

1. **Prerequisites:**
   - Python 3.11+
   - PostgreSQL running on port `5432`
   - Redis running on port `6379` (optional; API degrades gracefully to `X-Cache: BYPASS` if unavailable)

2. **Create virtual environment and install development dependencies:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements-dev.txt
   ```

3. **Configure environment:**
   Create `.env` from `.env.example` and set `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET_KEY`, and `SEED_ADMIN_PASSWORD`:
   ```bash
   cp .env.example .env
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Seed initial admin user, workspace, and project:**
   ```bash
   python -m app.core.seed
   ```

6. **Start development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 🧪 Testing & Code Quality

Run tests, type checks, and linters:

```bash
# Run full pytest test suite
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
| `TEST_DATABASE_URL` | Dedicated PostgreSQL test database URL | `None` |
| `REDIS_URL` | Redis server connection string | `redis://localhost:6379/0` |
| `CACHE_TTL_SECONDS` | Cache expiration time in seconds | `30` |
| `CACHE_PUBLIC_PATHS`| Public GET routes enabled for Redis caching | `/api/v1/workspaces, ...` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens (min 32 chars) | Required |
| `SEED_ADMIN_EMAIL` | Initial admin email used by `app.core.seed` | `owner@taskhub.dev` |
| `SEED_ADMIN_PASSWORD` | Initial admin password (min 12 chars; required in `production` or when seeding) | `None` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `INFO` |
| `LOG_JSON_FORMAT` | Enable structured JSON logging format | `true` |
| `TASK_QUEUE_SHUTDOWN_TIMEOUT_SECONDS` | Max seconds to wait for background tasks on shutdown | `5.0` |
