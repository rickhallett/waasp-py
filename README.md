# WAASP (Python)

> Security whitelist for agentic AI — Python implementation

A Python implementation of [wasp](https://github.com/rickhallett/wasp), demonstrating:
- Event-driven architecture with Celery
- SQLAlchemy + Alembic migrations
- Type-safe API with Pydantic
- Test-driven development
- Docker containerization
- AWS deployment ready

## Quick Start

### With Docker (recommended)

```bash
# Start all services
make up

# Run migrations
make migrate

# View logs
make logs
```

API available at http://localhost:8000

### Local Development

```bash
# Install dependencies
make install

# Start development server
make dev
```

## CLI Usage

```bash
# Check if a sender is allowed
waasp check "+447375862225"

# Add a trusted contact
waasp add "+447375862225" --name "Kai" --trust trusted

# List all contacts
waasp list

# Remove a contact
waasp remove "+447375862225"

# Start API server
waasp serve --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/check/` | Check if sender is allowed |
| `GET` | `/api/v1/check/<sender_id>` | Quick check (GET) |
| `GET` | `/api/v1/contacts/` | List all contacts |
| `POST` | `/api/v1/contacts/` | Add new contact |
| `PATCH` | `/api/v1/contacts/<sender_id>` | Update contact |
| `DELETE` | `/api/v1/contacts/<sender_id>` | Remove contact |
| `GET` | `/api/v1/audit/` | List audit logs |
| `GET` | `/api/v1/audit/stats` | Audit statistics |

## Trust Levels

| Level | Description |
|-------|-------------|
| `sovereign` | Full access. Can modify the whitelist. This is you. |
| `trusted` | Can trigger agent actions. Friends, family, colleagues. |
| `limited` | Agent sees the message but can't trigger dangerous actions. |
| `blocked` | Message never reaches the agent. Logged and dropped. |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INBOUND MESSAGE                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      WAASP API                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Flask API   │  │ SQLAlchemy  │  │  WhitelistService   │  │
│  │ + Pydantic  │◄─┤  + Alembic  │  │  + AuditService     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │  ALLOW    │  │  LIMITED  │  │   BLOCK   │
    │  → Agent  │  │  → Agent* │  │  → Log    │
    └───────────┘  └───────────┘  └───────────┘
```

## Development

```bash
# Run tests
make test

# Run linters
make lint

# Format code
make fmt

# All checks
make check
```

## Tech Stack

- **Backend:** Flask + Flask-Smorest (OpenAPI)
- **ORM:** SQLAlchemy 2.0 + Alembic
- **Validation:** Pydantic v2
- **Async:** Celery + Redis
- **Testing:** pytest + coverage
- **Linting:** ruff + mypy
- **Containerization:** Docker + Docker Compose

## License

MIT
