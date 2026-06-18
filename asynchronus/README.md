# Asynchronus Blog-Site

A modern, high-performance, and fully asynchronous blog application built using **FastAPI**. This backend leverages asynchronous database transactions, modern password hashing, token-based authentication, and automated email utilities to deliver a robust and secure blogging platform.

## 🚀 Tech Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous Web Framework)

- **Package Manager:** [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)

- **Database Engine:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async ORM) with [aiosqlite](https://github.com/n6nio/aiosqlite) (Async SQLite driver)

- **Security & Auth:** [Argon2-cffi](https://argon2-cffi.readthedocs.io/) / `pwdlib` for password hashing, and [PyJWT](https://pyjwt.readthedocs.io/) / `python-jose` for secure JWT authentication

- **Email Dispatch:** [aiosmtplib](https://github.com/cole/aiosmtplib) for asynchronous SMTP operations (e.g., verification, password resets)

- **Templating:** [Jinja2](https://jinja.github.io/jinja2/) for rendering server-side views or dynamic email templates

- **Validation:** [Pydantic v2](https://docs.pydantic.dev/) & `email-validator` for strict data schema enforcement

---

## 🛠️ Getting Started

### Prerequisites
Make sure you have **Python >= 3.12** and **uv** installed on your system. 

If you do not have `uv` installed, get it via:
```bash
# macOS/Linux
curl -LsSf https://astral-sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral-sh/uv/install.ps1 | iex"

Installation & Setup

1. Clone the repository:

Bash
git clone [https://github.com/your-username/asynchronus.git](https://github.com/your-username/asynchronus.git)
cd asynchronus

2. Create and sync the virtual environment using uv:

This will automatically read your pyproject.toml or requirements.txt and lock the exact dependencies:

Bash
uv sync


3. Activate the virtual environment:

Windows (PowerShell):

PowerShell
.venv\Scripts\Activate.ps1

Linux/macOS:

Bash
source .venv/bin/activate


4. Environment Variables Configuration:
Create a .env file in the root directory to store your application configurations:

Code snippet

DATABASE_URL=sqlite+aiosqlite:///./blog.db
SECRET_KEY=your_super_secret_jwt_signing_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SMTP Configurations (Optional for email features)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

5. 🏃 Running the Application
Start the local development server using Uvicorn with hot-reloading enabled:

Bash
uvicorn main:app --reload
The application will be accessible at: http://127.0.0.1:8000

🗺️ Interactive API Documentation
Once the server is running, you can explore, test, and interact with the endpoints directly from your browser:

Swagger UI: http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc

🗂️ Project Structure (Suggested)
Plaintext
asynchronus/
├── app/
│   ├── api/             # API routes (auth, posts, users, comments)
│   ├── core/            # App configurations, security, and hashing 
│   ├── models/          # SQLAlchemy async database models
│   ├── schemas/         # Pydantic data validation schemas
│   ├── services/        # Business logic & background tasks (email, media processing)
│   └── database.py      # Async engine and session configuration
├── templates/           # Jinja2 HTML templates
├── main.py              # FastAPI app initialization & setup
├── pyproject.toml       # Project metadata and dependencies managed by uv
├── requirements.txt     # Compiled dependencies
└── .env                 # Environment configuration values
🔒 Key Security Implementation Details
Password Safety: Raw passwords are never exposed; they are securely seasoned and hashed using Argon2id profiles.

Session Management: Secure JWT (JSON Web Tokens) are issued upon login to handle state-less authentication natively across requests.

Asynchronous Input Filtering: Built-in form-handling and file uploads processed smoothly using python-multipart and pillow.

