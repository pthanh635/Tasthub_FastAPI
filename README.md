# TaskHub API — Day 3: Authentication, Security, Authorization & RBAC

Hệ thống quản lý công việc (**Task Management API**) xây dựng bằng **FastAPI**, **SQLAlchemy 2.x Async ORM**, **PostgreSQL (`asyncpg`)**, **Alembic**, **JWT (`PyJWT`)**, **Bcrypt** và **Pydantic v2** theo kiến trúc **Layered Architecture + Repository Pattern + Dependency Injection**.

---

## 1. Tech Stack

- **Python**: 3.11+
- **Web Framework**: FastAPI (`>=0.115`)
- **Validation & Settings**: Pydantic v2, `pydantic-settings`
- **ORM & Database**: SQLAlchemy 2.x (Async ORM), PostgreSQL (`asyncpg`)
- **Database Migration**: Alembic (async template)
- **Authentication & Security**: `bcrypt` (password hashing), `PyJWT` (`HS256` Access & Refresh Tokens, Token Rotation & Revocation)
- **Testing**: `pytest`, `pytest-asyncio`, `httpx` (chạy trên database PostgreSQL test riêng biệt `taskhub_test`)
- **Code Quality**: `ruff`, `mypy` (strict mode)

---

## 2. Cây thư mục thực tế

```text
taskhub/
├── alembic/
│   ├── versions/
│   │   ├── 0001_initial_schema.py
│   │   ├── 0002_auth_and_rbac.py
│   │   └── 0003_cascade_and_indexes.py
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routers/
│   │       │   ├── auth.py
│   │       │   ├── projects.py
│   │       │   ├── tasks.py
│   │       │   ├── users.py
│   │       │   └── workspaces.py
│   │       └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   ├── security.py
│   │   └── seed.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── comment.py
│   │   ├── enums.py
│   │   ├── label.py
│   │   ├── project.py
│   │   ├── refresh_token.py
│   │   ├── task.py
│   │   ├── user.py
│   │   └── workspace.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── project_repository.py
│   │   ├── refresh_token_repository.py
│   │   ├── task_repository.py
│   │   ├── user_repository.py
│   │   └── workspace_repository.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── project.py
│   │   ├── task.py
│   │   ├── user.py
│   │   └── workspace.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── task_service.py
│   │   ├── user_service.py
│   │   └── workspace_service.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_auth_and_users.py
│   ├── test_database_and_models.py
│   ├── test_rbac_and_ownership.py
│   ├── test_repository_and_service.py
│   └── test_tasks.py
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── README.md
└── requirements.txt
```

---

## 3. Kiến trúc Authentication, RBAC & Resource Ownership

### 3.1. Authentication & Token Lifecycle
- **Password Hashing**: Mật khẩu người dùng được băm bằng `bcrypt` (`hash_password()`, `verify_password()`), tuyệt đối không lưu hoặc trả về plaintext/hash trong API response (`UserResponse`).
- **JWT Access & Refresh Tokens**:
  - **Access Token**: Thời hạn ngắn (`ACCESS_TOKEN_EXPIRE_MINUTES=30`), chứa `sub` (`user.id`), `role` (`ADMIN|MEMBER`), `type="access"`, `jti`, `iat`, `exp`.
  - **Refresh Token**: Thời hạn dài (`REFRESH_TOKEN_EXPIRE_DAYS=7`), chứa `sub`, `type="refresh"`, `jti`. Bản băm SHA-256 (`token_hash`) được lưu trong bảng `refresh_tokens`.
  - **Token Rotation & Revocation**: Khi gọi `POST /api/v1/auth/refresh`, refresh token cũ bị thu hồi (`revoked_at`) và cặp token mới được cấp phát. Khi gọi `POST /api/v1/auth/logout` hoặc đổi mật khẩu (`POST /api/v1/users/me/change-password`), refresh token bị thu hồi ngay lập tức.

### 3.2. Authorization, RBAC & Resource Ownership
- **Dependency `get_current_user`**: Xác thực Bearer JWT Access Token qua `HTTPBearer` (tích hợp nút `Authorize` trên Swagger UI), kiểm tra trạng thái `user.is_active`.
- **Global RBAC (`UserRole`)**: `ADMIN` và `MEMBER` (hỗ trợ dependency `require_global_roles(...)`).
- **Workspace RBAC (`WorkspaceRole`) & Resource Ownership**:
  - `OWNER`: Toàn quyền trên Workspace (chỉ `OWNER` hoặc global `ADMIN` mới được sửa/xóa Workspace; không thể bị xóa khỏi Workspace).
  - `ADMIN`: Quản lý thành viên (`POST / DELETE /workspaces/{id}/members`), quản lý Project và toàn bộ Task trong Workspace.
  - `EDITOR`: Tạo/cập nhật Project và Task. **Resource Ownership**: Khi xóa Task (`DELETE /api/v1/tasks/{id}`), `EDITOR` chỉ được xóa Task do chính mình tạo (`task.created_by_id == current_user.id`); không được xóa Task của người khác.
  - `VIEWER`: Chỉ có quyền xem (`GET`) thông tin Workspace, Project và Task; mọi thao tác ghi (`POST`, `PUT`, `PATCH`, `DELETE`) đều bị từ chối với `403 Forbidden`.

---

## 4. API Endpoints (Day 3)

### Auth & Users
| Method | Endpoint | Status | Mô tả |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | `201` / `409` | Đăng ký tài khoản mới |
| `POST` | `/api/v1/auth/login` | `200` / `401` | Đăng nhập nhận `access_token` & `refresh_token` |
| `POST` | `/api/v1/auth/refresh` | `200` / `401` | Làm mới và xoay vòng (rotate) cặp JWT token |
| `POST` | `/api/v1/auth/logout` | `204` / `401` | Thu hồi (revoke) refresh token hiện tại |
| `GET` | `/api/v1/users/me` | `200` / `401` | Xem thông tin hồ sơ người dùng hiện tại |
| `PATCH` | `/api/v1/users/me` | `200` / `401` | Cập nhật `full_name` của người dùng hiện tại |
| `POST` | `/api/v1/users/me/change-password` | `204` / `400` | Đổi mật khẩu và thu hồi toàn bộ refresh token cũ |

### Workspaces, Projects & Tasks (Yêu cầu Bearer Token)
| Method | Endpoint | Quyền yêu cầu | Mô tả |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workspaces` | Authenticated | Tạo workspace mới (người tạo thành `OWNER`) |
| `GET` | `/api/v1/workspaces` | Authenticated | Danh sách workspace mà user là thành viên |
| `GET` | `/api/v1/workspaces/{id}` | Member (`ALL`) | Chi tiết workspace |
| `PATCH` | `/api/v1/workspaces/{id}` | `OWNER` only | Cập nhật thông tin workspace |
| `DELETE` | `/api/v1/workspaces/{id}` | `OWNER` only | Xóa workspace |
| `GET` | `/api/v1/workspaces/{id}/members` | Member (`ALL`) | Danh sách thành viên trong workspace |
| `POST` | `/api/v1/workspaces/{id}/members` | `OWNER` / `ADMIN` | Mời thành viên hoặc cập nhật role |
| `DELETE` | `/api/v1/workspaces/{id}/members/{user_id}` | `OWNER` / `ADMIN` | Xóa thành viên khỏi workspace |
| `POST` | `/api/v1/workspaces/{id}/projects` | `OWNER` / `ADMIN` / `EDITOR` | Tạo project trong workspace |
| `GET` | `/api/v1/workspaces/{id}/projects` | Member (`ALL`) | Danh sách project trong workspace |
| `GET` | `/api/v1/projects/{id}` | Member (`ALL`) | Xem chi tiết project |
| `PATCH` | `/api/v1/projects/{id}` | `OWNER` / `ADMIN` / `EDITOR` | Cập nhật hoặc Archive project (`status=ARCHIVED`) |
| `GET` | `/api/v1/projects/{id}/tasks` | Member (`ALL`) | Danh sách task thuộc project |
| `POST` | `/api/v1/projects/{id}/tasks` | `OWNER` / `ADMIN` / `EDITOR` | Tạo task trong project (`created_by_id = current_user.id`) |
| `POST` | `/api/v1/tasks` | `OWNER` / `ADMIN` / `EDITOR` | Tạo task mới |
| `GET` | `/api/v1/tasks` | Member (`ALL`) | Danh sách task trong các workspace mà user tham gia |
| `GET` | `/api/v1/tasks/{id}` | Member (`ALL`) | Chi tiết task theo UUID |
| `PUT` | `/api/v1/tasks/{id}` | `OWNER` / `ADMIN` / `EDITOR` | Cập nhật toàn bộ trường chỉnh sửa của task |
| `PATCH` | `/api/v1/tasks/{id}` | `OWNER` / `ADMIN` / `EDITOR` | Cập nhật một phần (partial update) task |
| `DELETE` | `/api/v1/tasks/{id}` | Task Creator (`EDITOR`) / `OWNER` / `ADMIN` | Xóa task (kiểm tra Resource Ownership) |

---

## 5. Hướng dẫn chạy Migrations, Server & Tests

```bash
# 1. Kích hoạt môi trường ảo
.\.venv\Scripts\activate

# 2. Chạy toàn bộ Alembic migration lên head
alembic upgrade head

# 3. Seed dữ liệu mẫu (giá trị lấy từ SEED_ADMIN_EMAIL và SEED_ADMIN_PASSWORD)
python -m app.core.seed

# 4. Khởi động API server
uvicorn app.main:app --reload

# 5. Chạy kiểm thử và kiểm tra chất lượng code
python -m pytest -v
ruff check .
mypy .
```
