# Sanjog's Blog

A modern, fully asynchronous blog platform built with **FastAPI** — featuring role-based access control, JWT authentication, email-based password recovery, profile image uploads, and a server-rendered frontend.

## 🚀 Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous Web Framework)
- **Package Manager:** [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)
- **Database:** [PostgreSQL](https://www.postgresql.org/) via [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async ORM) with [asyncpg](https://github.com/MagicStack/asyncpg)
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/) for versioned, reversible schema changes
- **Security & Auth:** `pwdlib` (Argon2) for password hashing, `PyJWT` for stateless JWT authentication
- **Role-Based Access Control:** Three-tier permission system — `user`, `admin`, and a fixed `superadmin` — backed by a many-to-many roles table
- **Email Dispatch:** [aiosmtplib](https://github.com/cole/aiosmtplib) for asynchronous SMTP (password reset emails)
- **Image Processing:** [Pillow](https://pillow.readthedocs.io/) for profile picture resizing, cropping, and EXIF correction
- **Templating:** [Jinja2](https://jinja.palletsprojects.com/) for server-rendered pages and HTML emails
- **Validation:** [Pydantic v2](https://docs.pydantic.dev/) & `email-validator` for strict schema enforcement
- **Frontend:** Server-rendered Jinja2 templates styled with Bootstrap 5, plain JavaScript for API calls (no build step)

---

## ✨ Features

- **Authentication** — registration, login (JWT via OAuth2 password flow), and a "current user" endpoint
- **Posts** — create, read, update, delete, with pagination (`skip`/`limit`) on both the API and the server-rendered pages
- **Profile pictures** — upload, automatic resize/crop to a square, and deletion, handled by Pillow
- **Password recovery** — "forgot password" email flow using single-use, hashed, expiring tokens, plus an in-account "change password" option for logged-in users
- **Role-Based Access Control (RBAC)**
  - `user` — manage their own posts and account
  - `admin` — moderate any post or user account, but cannot change roles
  - `superadmin` — everything an admin can do, plus promote/demote users between `user` and `admin`; this role is fixed and can only ever be granted via `.env` configuration, never through the API
  - A dedicated `/admin` panel for user and role management
- **Versioned schema migrations** via Alembic — no more dropping the database to apply a model change

---

## 🛠️ Getting Started

### Prerequisites

- **Python >= 3.12**
- **[uv](https://github.com/astral-sh/uv)** for dependency management
- **PostgreSQL** running locally (or accessible remotely)

If you don't have `uv` installed:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installation & Setup

**1. Clone the repository:**

```bash
git clone https://github.com/your-username/sanjogs-blog.git
cd sanjogs-blog
```

**2. Create and sync the virtual environment:**

```bash
uv sync
```

**3. Activate the virtual environment:**

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# Linux/macOS
source .venv/bin/activate
```

**4. Set up PostgreSQL:**

Create a database and a dedicated user:

```bash
psql -U postgres
```

```sql
CREATE USER bloguser WITH PASSWORD 'your_password_here';
CREATE DATABASE blogdb OWNER bloguser;
\q
```

**5. Configure environment variables:**

Create a `.env` file in the project root:

```dotenv
# Database
DATABASE_URL=postgresql+asyncpg://bloguser:your_password_here@localhost:5432/blogdb

# JWT / Auth
SECRET_KEY=your_super_secret_jwt_signing_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# RBAC — this account automatically receives the superadmin role on startup
SUPERADMIN_EMAIL=you@example.com

# Password reset
RESET_TOKEN_EXPIRE_MINUTES=60
FRONTEND_URL=http://localhost:8000

# SMTP (e.g. Mailtrap sandbox for local development)
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=587
MAIL_USERNAME=your_mailtrap_username
MAIL_PASSWORD=your_mailtrap_password
MAIL_FROM=noreply@example.com
MAIL_USE_TLS=true

# Misc
MAX_UPLOAD_SIZE_BYTES=5242880
POST_PER_PAGE=10
```

> **Note:** `SUPERADMIN_EMAIL` must match the email of a registered account for the role to be attached. If the account doesn't exist yet, register it first, then restart the server so the role-seeding logic can find and promote it.

**6. Apply database migrations:**

```bash
uv run alembic upgrade head
```

This creates every table (`users`, `posts`, `roles`, `user_roles`, `password_reset_tokens`) using Alembic's versioned migrations, rather than a one-shot schema dump.

**7. Run the application:**

```bash
uv run fastapi dev main.py
```

On startup, the app automatically seeds the three roles (`user`, `admin`, `superadmin`) and attaches the `superadmin` role to whichever account matches `SUPERADMIN_EMAIL`.

The application will be accessible at: **http://127.0.0.1:8000**

---

## 🗺️ Interactive API Documentation

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## 🗂️ Project Structure

```
asynchronus/
├── alembic/
│   ├── env.py                  # Alembic ↔ async SQLAlchemy bridge
│   └── versions/                # Generated migration files
├── media/
│   └── profile_pics/            # Uploaded, processed profile pictures
├── routers/
│   ├── authenticate.py          # Register, login, /me, password reset
│   ├── users.py                 # User CRUD, profile pictures, pagination
│   ├── posts.py                 # Post CRUD, pagination
│   └── rbac.py                  # Role seeding + promote/demote endpoints
├── static/
│   ├── js/
│   │   ├── auth.js              # Token storage, navbar auth state
│   │   └── utils.js             # Modals, theme toggle, post actions
│   └── style.css
├── templates/
│   ├── email/
│   │   └── password-reset.html  # Table-based HTML email template
│   ├── base.html
│   ├── home.html
│   ├── post.html
│   ├── users_post.html
│   ├── account.html
│   ├── admin.html               # RBAC user management panel
│   ├── login.html / register.html
│   ├── forgot_password.html / reset_password.html
│   └── error.html
├── alembic.ini
├── auth.py                      # JWT creation/verification, password hashing, CurrentUser dependency
├── config.py                    # Pydantic Settings, loaded from .env
├── database.py                  # Async engine, session factory
├── email_utils.py                # SMTP email construction and sending
├── image_utils.py                # Pillow-based profile picture processing
├── models.py                     # SQLAlchemy ORM models
├── schema.py                     # Pydantic request/response schemas
├── main.py                       # FastAPI app, page routes, lifespan
├── pyproject.toml
└── .env
```

---

## 🔒 Key Security Implementation Details

- **Password safety** — passwords are never stored in plaintext; they're hashed with Argon2 via `pwdlib`.
- **Stateless authentication** — JWTs are issued on login and verified on every protected request via a `CurrentUser` dependency, with no server-side session storage required.
- **Password reset tokens are hashed at rest** — the raw token is only ever sent by email; the database stores only its SHA-256 hash, and each token is deleted immediately after a single successful use.
- **User enumeration resistance** — the "forgot password" endpoint returns an identical response whether or not the submitted email matches an account.
- **Role-based authorization** — every privileged action (editing another user's post, promoting an account) is enforced server-side via a reusable `require_role` dependency and explicit ownership checks; frontend role-based UI (e.g. hiding the Admin panel) is a convenience layer only, never the actual security boundary.
- **The superadmin role cannot be granted through the API** — it is only ever assigned via the `SUPERADMIN_EMAIL` environment variable at startup, and that account can never be deleted or have its roles modified by any other user.

---

## 🔄 Database Migrations

Whenever a model in `models.py` changes, generate and apply a new migration rather than recreating the database:

```bash
uv run alembic revision --autogenerate -m "describe your change"
uv run alembic upgrade head
```

To roll back the most recent migration:

```bash
uv run alembic downgrade -1
```