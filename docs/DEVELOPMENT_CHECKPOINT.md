# FixCare Development Checkpoint

**Last updated:** 2026-08-16  
**Branch:** `main`

## Current verified baseline

FixCare is a Flutter + FastAPI + PostgreSQL application with Docker Compose, SQLAlchemy/Alembic, and an AI-provider abstraction.

### Backend status

- Python virtual environment: Python 3.12.10
- FastAPI: 0.115.0
- SQLAlchemy: 2.0.35
- Pydantic: 2.9.2
- PostgreSQL 16 Alpine: running successfully in Docker
- Alembic initial migration: applied successfully
- FastAPI backend import smoke test: passed
- Full backend regression suite: **37 passed, 0 failed**
- Diagnosis endpoint runtime verification reached **201 Created** during the Flutter integration session
- Diagnosis result persistence/querying was observed successfully in PostgreSQL logs

Run the regression suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Major problems found and fixed

### 1. API circular import

`health.py` imported `api_router` from `app.api.router`, while the router imported the v1 modules. The unnecessary import was removed.

Result:

```text
FixCare backend imports OK
```

### 2. SQLAlchemy typo

In `backend/app/db/models/diagnosis.py`:

```python
mapped.column(...)
```

was corrected to:

```python
mapped_column(...)
```

### 3. Missing `RiskLevel`

`backend/app/services/diagnosis_service.py` used `RiskLevel` without importing it. The required enum import was added.

### 4. structlog configuration

`backend/app/core/logging.py` incorrectly attempted to access `structlog.INFO`. The filtering-bound-logger configuration was corrected.

### 5. Alembic configuration

`alembic.ini` was missing `script_location`, causing:

```text
FAILED: No 'script_location' key found in configuration.
```

The configuration was fixed.

Migration now succeeds with:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### 6. Safety severity ranking

The safety service originally used Python `max()` directly on a string-backed `RiskLevel` enum. That does not represent the intended severity ordering.

The correct ordering is:

```text
SAFE < LOW < MODERATE < HIGH < CRITICAL
```

An explicit ranking map was added. This fixed swollen-battery, burning-smell, water-damage, and multiple-risk severity handling.

### 7. Swollen-battery escalation reason

The mock AI provider detected swollen batteries correctly but returned only a generic escalation message. The provider was updated to preserve the hazard context and explicitly reference the swollen/bulging battery.

### 8. Flutter/FastAPI diagnosis JSON contract

Flutter models initially generated camelCase JSON names while FastAPI/Pydantic expects snake_case field names.

The diagnosis request was changed to use an explicit `toJson()` wire contract, including:

```text
device_category
problem_description
device_id
brand
model
follow_up_answers
```

Response models use explicit `JsonKey` mappings where required, including `device_category`, `problem_summary`, `technician_required`, `technician_reason`, `created_at`, `updated_at`, and `completed_at`.

### 9. Redundant datasource serialization bug

The remote datasource was converting already-serialized request data a second time by looking up camelCase keys. This produced null request values and caused FastAPI `422` validation errors:

```text
Input should be 'mobile', 'laptop' or 'tv'
Input should be a valid string
```

The datasource was simplified to:

```dart
final data = request.toJson();
```

and sends that payload directly to `/diagnosis`.

### 10. Flutter generic `No Internet` error

Flutter displayed a generic `No Internet` message even though the backend was running. The actual logs showed requests to:

```text
http://10.0.2.2:8000/api/v1/diagnosis
```

FastAPI `/docs` and `/openapi.json` returned `200 OK`, and the diagnosis endpoint later returned `201 Created`. The important lesson is to inspect the actual Dio exception/status rather than treating a generic client error as proof of lost internet connectivity.

### 11. Flutter debug connection issue

A later emulator launch produced:

```text
Error waiting for a debug connection: The log reader stopped unexpectedly
```

This was treated as a Flutter/Android debug connection issue rather than evidence of a new Dart or backend source failure. No broad rewrite was made.

## Testing history

The documented backend regression baseline:

```text
37 passed
0 failed
```

Relevant targeted checks also passed:

```text
3 safety tests passed
1 swollen-battery AI-provider test passed
```

During runtime integration, the backend also demonstrated:

```text
GET /docs -> 200 OK
GET /openapi.json -> 200 OK
POST /api/v1/diagnosis -> 201 Created
```

## Docker / PostgreSQL

Docker Desktop is working.

PostgreSQL service:

```text
image: postgres:16-alpine
database: fixcare
user: fixcare
port: 5432
```

Useful commands:

```powershell
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U fixcare -d fixcare
```

The database reported:

```text
/var/run/postgresql:5432 - accepting connections
```

The full backend stack can be started with:

```powershell
docker compose up -d
```

Docker Compose currently warns that the `version: '3.8'` field is obsolete. Removing that field is a future cleanup task.

## Git checkpoint

The stable code checkpoint is:

```text
963f792 checkpoint: stable frontend and backend state
```

The 2026-08-16 debugging record is documented in:

```text
docs/DEVELOPMENT_LOG_2026-08-16.md
```

The backend virtual environment is intentionally ignored and must never be committed.

Before future commits:

```powershell
git status --short
git diff --stat
git diff
```

Review all changes before staging.

## Important files

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── schemas/
│   └── services/
├── alembic/
├── tests/
├── Dockerfile
├── requirements.txt
└── alembic.ini

frontend/
.github/
docker-compose.yml
README.md
docs/
├── DEVELOPMENT_CHECKPOINT.md
└── DEVELOPMENT_LOG_2026-08-16.md
progress.txt
```

## Recommended development workflow

For every bug:

```text
1. Reproduce
2. Identify the failing component
3. Inspect the implementation
4. Make the smallest correct change
5. Run a targeted test
6. Run the full regression suite
7. Review git diff
8. Update documentation
9. Commit
```

Do not make broad rewrites while debugging.

## Current next milestone

The backend foundation and diagnosis API contract are checkpointed. The next session should focus on runtime verification and the user-facing diagnosis flow:

```text
Device selection
→ Problem input
→ Diagnosis request
→ Loading state
→ Follow-up questions when required
→ Diagnosis result
→ Safety warnings
→ History persistence
→ Feedback
```

Before changing networking or serialization code, reproduce the problem and inspect the actual request/response first.

## Safe resume procedure

### 1. Verify repository state

```powershell
git status
git log -5 --oneline
```

### 2. Start PostgreSQL

```powershell
docker compose up -d postgres
docker compose ps
```

### 3. Start FastAPI

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify API

Open:

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

### 5. Start Flutter

From `frontend`:

```powershell
flutter pub get
flutter run
```

Do not regenerate code unless source models were intentionally changed.

### 6. Test diagnosis

Confirm the request contains non-null:

```text
device_category
problem_description
```

Then confirm:

```text
201 Created
```

### 7. Continue UI work

If the API contract is healthy, continue with the diagnosis result/follow-up UI rather than changing networking or serialization layers.

## Do not do this on resume

Do not immediately run:

```text
flutter clean
flutter pub upgrade
build_runner clean
build_runner build
```

and do not rewrite diagnosis models, ApiClient, or backend schemas without a concrete reproducible failure.

## Documentation rule

Every meaningful bug should be recorded with:

```text
Symptom
Root cause
Fix
Verification
```

This prevents repeated debugging of the same problem.

## Safety rule for future AI work

Real AI providers must remain behind the FixCare safety validation layer. Do not bypass safety screening or validation when integrating OpenAI, Gemini, Anthropic, or another provider.
