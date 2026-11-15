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
## Database Initialization

Run from the repository root:

```powershell
python -m services.backend.app.database.init_db
```

Creates missing tables without deleting existing records.
This command does not migrate or update existing table definitions.

## Database Models

- User: user identity and enrollment status.
- Device: owner, public key, pairing status, and revocation time.
- Session: owner, state, expiration, and re-authentication timestamps.
- AuthChallenge: user, device, session, purpose, expiration, and consumption time.
- SecurityEvent: event details and optional session reference.

SQLite foreign key enforcement is enabled for application connections.
Cross-record ownership checks and authentication policies must also be
enforced by the authentication service.

Enrollment and pairing statuses currently default to PENDING.
New sessions default to LOCKED; state transition rules are defined in BE-04.

Device private keys, vault passwords, decryption keys, and real biometric
templates must not be stored in these models.
Security event metadata must be sanitized before insertion.

## Database Tests

```powershell
python -m pytest tests/integration/test_database_models.py -v
```

Tests use a temporary SQLite database and cover table creation,
related records, foreign key enforcement, and duplicate user IDs.