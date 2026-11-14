# Backend

FastAPI backend using SQLAlchemy and SQLite.
Python 3.11 or newer is required.

Run all commands from the repository root.

## Installation

```powershell
python -m pip install -r services/backend/requirements.txt
```

## Configuration

If `.env` does not exist, copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Configuration:

```dotenv
DATABASE_URL=sqlite:///./backend.db
```

Existing environment variables take precedence over `.env`.
The default SQLite database is created in the working directory.
Local `.env` and database files must not be committed.

## Running

```powershell
python -m uvicorn services.backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Health Check

Open http://127.0.0.1:8000/health

Successful response:

```json
{"status":"ok","database":"ok"}
```

Startup fails if the database connection cannot be established.
If the database becomes unavailable after startup, `/health` returns HTTP 503.

API documentation: http://127.0.0.1:8000/docs

Database models and table initialization will be implemented in BE-02.
## Tests

Install test dependencies:

```powershell
python -m pip install pytest httpx
```

Run the backend health tests from the repository root:

```powershell
python -m pytest tests/integration/test_backend_health.py -v
```

Tests use a temporary SQLite database and cover successful health checks
and database connection failures.