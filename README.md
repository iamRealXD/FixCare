# FixCare

A structured device troubleshooting platform powered by AI.

## Architecture

```
Flutter Frontend
       ��
FastAPI Backend (REST API)
       ��
Diagnosis Service
       ��
AI Provider Abstraction (OpenAI, Gemini, Anthropic, Mock)
       ��
PostgreSQL Database
```

## Features

- **Device Diagnosis**: Natural language problem description → structured diagnosis
- **Multi-device Support**: Mobile phones, laptops, TVs
- **Safety-First**: Automatic escalation for dangerous conditions (swollen battery, smoke, high voltage)
- **Structured Output**: Likely causes, safe troubleshooting steps, risk assessment
- **AI Provider Abstraction**: Switch between OpenAI, Gemini, Anthropic, or mock provider
- **Diagnosis History**: Persistent storage of all diagnoses and feedback
- **Device Profiles**: Register and manage personal devices
- **Authentication**: JWT-based auth (register, login, logout)

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API routes (health, diagnosis, devices, users, auth)
│   │   ├── core/             # Config, logging, security, exceptions
│   │   ├── db/               # Database models, migrations
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (diagnosis, safety, AI providers)
│   │   └── main.py           # FastAPI application
│   ├── alembic/              # Database migrations
│   ├── tests/                # Unit and integration tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── lib/
│   │   ├── app/              # App configuration, router, theme
│   │   ├── core/             # Network, errors, logging, storage, utils
│   │   └── features/         # Feature modules (diagnosis, history, devices, auth, settings)
│   ├── test/                 # Unit and widget tests
│   └── pubspec.yaml
│
├── docker-compose.yml
��── README.md
```

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Flutter 3.24+ (for frontend)
- Docker & Docker Compose (optional)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Get dependencies
flutter pub get

# Run the app
flutter run
```

### Docker Setup (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development, staging, production) | `development` |
| `API_HOST` | API host | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `AI_PROVIDER` | AI provider (mock, openai, gemini, anthropic) | `mock` |
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI |
| `GEMINI_API_KEY` | Google Gemini API key | Required for Gemini |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required for Anthropic |
| `JWT_SECRET` | JWT signing secret | Required |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `LOG_LEVEL` | Log level | `INFO` |

## API Documentation

When running in development mode:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Key Endpoints

```
POST   /api/v1/auth/register     - Register new user
POST   /api/v1/auth/login        - Login
POST   /api/v1/diagnosis         - Create and run diagnosis
GET    /api/v1/diagnosis/{id}    - Get diagnosis details
GET    /api/v1/diagnosis         - List user diagnoses
POST   /api/v1/diagnosis/{id}/feedback - Submit feedback
POST   /api/v1/devices           - Register device
GET    /api/v1/devices           - List devices
GET    /api/v1/devices/{id}      - Get device details
PATCH  /api/v1/devices/{id}      - Update device
DELETE /api/v1/devices/{id}      - Delete device
GET    /api/v1/users/me          - Get current user
PATCH  /api/v1/users/me          - Update current user
GET    /api/v1/health            - Health check
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_safety_service.py
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
flutter test

# Run integration tests
flutter test integration_test/
```

## AI Provider Configuration

FixCare supports multiple AI providers through a unified abstraction:

### Mock Provider (Default)
No API key required. Returns deterministic responses for testing.

```env
AI_PROVIDER=mock
```

### OpenAI
```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Google Gemini
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=...
```

### Anthropic Claude
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
```

## Safety System

FixCare includes a comprehensive safety system that automatically detects and escalates dangerous conditions:

- **Critical**: Swollen battery, smoke, sparks, electrical shock, burning smell
- **High**: Water damage, high voltage (TV internals), battery leakage
- **Moderate**: Exposed wiring, overheating, structural damage

When critical conditions are detected, the system:
1. Stops troubleshooting immediately
2. Provides clear safety warnings
3. Recommends professional technician
4. Marks diagnosis as escalated

## Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):

- Code formatting (ruff, dart format)
- Linting (ruff, flutter analyze)
- Type checking (mypy)
- Unit tests (pytest, flutter test)
- Build verification

## Production Deployment

1. Set `APP_ENV=production`
2. Use strong `JWT_SECRET`
3. Configure production `DATABASE_URL`
4. Set up reverse proxy (Caddy, Nginx, Traefik) for HTTPS
5. Configure AI provider with production API keys
6. Run database migrations: `alembic upgrade head`
7. Start with: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Roadmap

- [ ] MVP: Core diagnosis flow with mock AI
- [ ] Authentication & user accounts
- [ ] Diagnosis history & feedback
- [ ] Device profiles
- [ ] Production hardening (rate limiting, observability)
- [ ] Knowledge base & RAG integration
- [ ] Multi-provider AI routing
- [ ] Fine-tuned FixCare proprietary model
- [ ] Computer vision (photo-based diagnosis)
- [ ] Voice input
- [ ] Technician marketplace

## Security

- No secrets in repository (use `.env`)
- HTTPS in production via reverse proxy
- Input validation on all endpoints
- JWT authentication with secure defaults
- Safety system prevents dangerous instructions
- Structured logging without sensitive data

## License

MIT License - see LICENSE file for details.